// Uploads staged files one by one, collecting what was added and what went wrong.
import { ApiError, sessionsApi, type UploadedAttachment } from "../../lib/sessions";
import type { StagedFile } from "./FilePicker";

export type UploadResult = { added: UploadedAttachment[]; failed: StagedFile[]; problems: string[] };

export async function uploadStaged(sessionId: string, files: StagedFile[]): Promise<UploadResult> {
  const result: UploadResult = { added: [], failed: [], problems: [] };
  for (const staged of files) {
    if (staged.role === null) continue;
    try {
      const uploaded = await sessionsApi.attach(sessionId, staged.file, staged.role);
      if (uploaded.duplicate) result.problems.push(`${staged.file.name} is already attached as ${uploaded.id}`);
      else result.added.push(uploaded);
    } catch (caught) {
      result.failed.push(staged);
      result.problems.push(caught instanceof ApiError ? caught.message : `${staged.file.name} could not be uploaded`);
    }
  }
  return result;
}
