use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use tauri::Emitter;
use tauri_plugin_shell::ShellExt;

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
    run_engine(&request, &app_handle).map(|stdout| EngineResult { stdout })
}

fn run_engine(
    request: &GenerateRequest,
    app_handle: &tauri::AppHandle,
) -> Result<String, String> {
    let mut envs = HashMap::new();

    if !request.api_key.trim().is_empty() {
        let env_key = if request.llm_provider == "anthropic-messages" {
            "ANTHROPIC_API_KEY"
        } else {
            "OPENAI_API_KEY"
        };
        envs.insert(env_key.to_string(), request.api_key.clone());
    }

    let (mut rx, _child) = app_handle
        .shell()
        .sidecar("docforge-engine")
        .map_err(|e| format!("failed to resolve engine sidecar: {e}"))?
        .args([
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
        .envs(envs)
        .spawn()
        .map_err(|e| format!("failed to spawn engine: {e}"))?;

    let mut stdout = String::new();

    use tauri_plugin_shell::process::CommandEvent;
    while let Some(event) = rx.blocking_recv() {
        match event {
            CommandEvent::Stdout(line) => {
                let line = String::from_utf8_lossy(&line).to_string();
                stdout.push_str(&line);
                stdout.push('\n');
            }
            CommandEvent::Stderr(line) => {
                let line = String::from_utf8_lossy(&line).to_string();
                if let Some(ref h) = Some(app_handle) {
                    let _ = h.emit("engine-progress", &line);
                }
            }
            CommandEvent::Terminated(status) => {
                if !status.code.map_or(true, |c| c == 0) {
                    return Err(format!("engine process exited with status {:?}", status.code));
                }
            }
            CommandEvent::Error(e) => {
                return Err(format!("engine error: {e}"));
            }
            _ => {}
        }
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
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![generate_docx, validate_path, load_settings, save_settings])
        .run(tauri::generate_context!())
        .expect("failed to run tauri application");
}
