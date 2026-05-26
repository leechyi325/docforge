use serde::{Deserialize, Serialize};
use std::env;
use std::path::Path;
use std::process::Command;

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
fn generate_docx(request: GenerateRequest) -> Result<EngineResult, String> {
    let mut errors = Vec::new();

    for python in python_candidates() {
        match run_engine(&python, &request) {
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

fn run_engine(python: &str, request: &GenerateRequest) -> Result<String, String> {
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
        .current_dir(repo_root());

    if !request.api_key.trim().is_empty() {
        let env_key = if request.llm_provider == "anthropic-messages" {
            "ANTHROPIC_API_KEY"
        } else {
            "OPENAI_API_KEY"
        };
        command.env(env_key, &request.api_key);
    }

    let output = command.output().map_err(|error| error.to_string())?;

    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).to_string());
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

fn repo_root() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .and_then(Path::parent)
        .expect("src-tauri should live under apps/desktop/src-tauri")
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![generate_docx])
        .run(tauri::generate_context!())
        .expect("failed to run tauri application");
}
