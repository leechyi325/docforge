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
    api_key: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct EngineResult {
    stdout: String,
}

#[tauri::command]
fn generate_docx(request: GenerateRequest) -> Result<EngineResult, String> {
    let python = env::var("DOCFORGE_PYTHON").unwrap_or_else(|_| "python3".to_string());
    let output = run_engine(&python, &request).or_else(|first_error| {
        if python == "python3" {
            run_engine("python", &request)
                .map_err(|second_error| format!("{first_error}; fallback failed: {second_error}"))
        } else {
            Err(first_error)
        }
    })?;

    Ok(EngineResult { stdout: output })
}

fn run_engine(python: &str, request: &GenerateRequest) -> Result<String, String> {
    let output = Command::new(python)
        .args([
            "-m",
            "engine.cli",
            "generate",
            "--input",
            &request.input_path,
            "--profile",
            &request.profile,
            "--format-instruction",
            &request.format_instruction,
            "--llm-provider",
            &request.llm_provider,
            "--api-key",
            &request.api_key,
            "--output",
            &request.output_path,
        ])
        .current_dir(repo_root())
        .output()
        .map_err(|error| error.to_string())?;

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
