export type ProfileId = "general" | "official" | "meeting_minutes" | "briefing" | "speech";

export type LlmProvider = "local" | "openai-responses" | "openai-compatible" | "anthropic-messages";

export type Issue = {
  id: string;
  severity: "info" | "warning" | "error";
  message: string;
  location: {
    type: "document" | "paragraph" | "section";
    index: number | null;
    key: string | null;
  };
  fix_action: unknown | null;
};

export type GenerateRequest = {
  inputPath: string;
  outputPath: string;
  profile: ProfileId;
  formatInstruction: string;
  llmProvider: LlmProvider;
  llmModel: string;
  llmBaseUrl: string;
  apiKey: string;
};

export type GenerateResponse = {
  output: string;
  issues: Issue[];
};

export type PathValidation = {
  valid: boolean;
  error: string | null;
};
