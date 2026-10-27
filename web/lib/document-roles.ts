// What a user says an attached file is (SPEC-document-import §2.1): the importer reads a PRD,
// a technical spec and a supporting document each with different expectations.
import type { UploadedAttachment } from "./sessions";

export type DocumentRole = UploadedAttachment["role"];

export const DOCUMENT_ROLES: { value: DocumentRole; label: string; hint: string }[] = [
  { value: "prd", label: "PRD", hint: "Product requirements: the problem, users, goals and requirements" },
  { value: "spec", label: "Spec", hint: "A technical spec: data, API, architecture and scale" },
  { value: "supporting", label: "Supporting", hint: "Diagrams, notes, research or earlier work" },
];

export function roleLabel(role: DocumentRole): string {
  return DOCUMENT_ROLES.find((r) => r.value === role)?.label ?? role;
}
