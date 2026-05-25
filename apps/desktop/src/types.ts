export type ProfileId = "general" | "official" | "meeting_minutes" | "briefing" | "speech";

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
