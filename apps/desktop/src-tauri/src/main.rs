use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::Command;
use tauri::Emitter;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GenerateRequest {
    input_path: String,
    output_path: String,
    profile: String,
    format_instruction: String,
    llm_provider: String,
    llm_model: String,
    llm_base_url: String,
    api_key: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct EngineResult {
    stdout: String,
}

#[tauri::command]
fn generate_docx(request: GenerateRequest, app_handle: tauri::AppHandle) -> Result<EngineResult, String> {
    let mut errors = Vec::new();

    for python in python_candidates() {
        match run_engine(&python, &request, Some(&app_handle)) {
            Ok(output) => return Ok(EngineResult { stdout: output }),
            Err(error) => errors.push(format!("{python}: {error}")),
        }
    }

    Err(errors.join("; fallback failed: "))
}

fn python_candidates() -> Vec<String> {
    let mut candidates = Vec::new();

    if let Ok(python) = env::var("DOCFORGE_PYTHON") {
        push_candidate(&mut candidates, python);
    }

    let venv_python = repo_root().join(".venv/bin/python");
    if venv_python.exists() {
        push_candidate(&mut candidates, venv_python.to_string_lossy().to_string());
    }

    push_candidate(&mut candidates, "python3".to_string());
    push_candidate(&mut candidates, "python".to_string());
    candidates
}

fn push_candidate(candidates: &mut Vec<String>, python: String) {
    if !python.trim().is_empty() && !candidates.iter().any(|candidate| candidate == &python) {
        candidates.push(python);
    }
}

fn run_engine(
    python: &str,
    request: &GenerateRequest,
    app_handle: Option<&tauri::AppHandle>,
) -> Result<String, String> {
    let mut command = Command::new(python);
    command
        .args([
            "-m",
            "engine.cli",
            "format",
            "--input",
            &request.input_path,
            "--profile",
            &request.profile,
            "--format-instruction",
            &request.format_instruction,
            "--llm-provider",
            &request.llm_provider,
            "--llm-model",
            &request.llm_model,
            "--llm-base-url",
            &request.llm_base_url,
            "--output",
            &request.output_path,
        ])
        .current_dir(repo_root())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped());

    if !request.api_key.trim().is_empty() {
        let env_key = if request.llm_provider == "anthropic-messages" {
            "ANTHROPIC_API_KEY"
        } else {
            "OPENAI_API_KEY"
        };
        command.env(env_key, &request.api_key);
    }

    let mut child = command.spawn().map_err(|error| error.to_string())?;

    // Stream stderr progress events in a background thread
    if let Some(stderr) = child.stderr.take() {
        let handle = app_handle.cloned();
        std::thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines().map_while(Result::ok) {
                if let Some(ref h) = handle {
                    let _ = h.emit("engine-progress", &line);
                }
            }
        });
    }

    // Read stdout
    let mut stdout = String::new();
    if let Some(out) = child.stdout.take() {
        let reader = BufReader::new(out);
        for line in reader.lines().map_while(Result::ok) {
            stdout.push_str(&line);
            stdout.push('\n');
        }
    }

    let status = child.wait().map_err(|error| error.to_string())?;
    if !status.success() {
        return Err("engine process failed".to_string());
    }

    Ok(stdout)
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct PathValidation {
    valid: bool,
    error: Option<String>,
}

#[tauri::command]
fn validate_path(path: String, path_type: String) -> PathValidation {
    let p = PathBuf::from(&path);

    if path_type == "input" {
        if !p.exists() {
            return PathValidation { valid: false, error: Some("文件不存在".to_string()) };
        }
        let suffix = p.extension().and_then(|e| e.to_str()).unwrap_or("");
        if suffix == "doc" {
            return PathValidation { valid: false, error: Some("不支持 .doc 格式，请使用 .docx 或 .md".to_string()) };
        }
        if suffix != "md" && suffix != "markdown" && suffix != "docx" {
            return PathValidation { valid: false, error: Some("仅支持 .md 和 .docx 格式".to_string()) };
        }
    }

    if path_type == "output" {
        let suffix = p.extension().and_then(|e| e.to_str()).unwrap_or("");
        if suffix != "docx" {
            return PathValidation { valid: false, error: Some("输出文件必须是 .docx 格式".to_string()) };
        }
    }

    PathValidation { valid: true, error: None }
}

fn repo_root() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .and_then(Path::parent)
        .expect("src-tauri should live under apps/desktop/src-tauri")
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppSettings {
    llm_provider: String,
    llm_model: String,
    llm_base_url: String,
    api_key: String,
}

fn settings_path() -> PathBuf {
    dirs_next::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".docforge")
        .join("settings.json")
}

#[tauri::command]
fn load_settings() -> Result<AppSettings, String> {
    let path = settings_path();
    if !path.exists() {
        return Ok(AppSettings {
            llm_provider: "local".to_string(),
            llm_model: String::new(),
            llm_base_url: String::new(),
            api_key: String::new(),
        });
    }
    let data = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    serde_json::from_str(&data).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_settings(settings: AppSettings) -> Result<(), String> {
    let path = settings_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let data = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
    fs::write(&path, data).map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![generate_docx, validate_path, load_settings, save_settings])
        .run(tauri::generate_context!())
        .expect("failed to run tauri application");
}
