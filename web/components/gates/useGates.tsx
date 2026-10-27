"use client";

// Approval gates are frontend tools rendered as cards (PRD D5, SPECS S11.4): the step
// confirmations, the gap decisions, the import review and the PRD sign-off.
import { useHumanInTheLoop } from "@copilotkit/react-core/v2";
import type { ComponentType } from "react";
import { z } from "zod";
import type { PrdDoc } from "../../lib/state";
import { ConfirmStepCard, type ConfirmStepArgs } from "./ConfirmStepCard";
import { type CardGap, DecideGapsCard } from "./DecideGapsCard";
import { type CardCandidate, ReviewImportCard } from "./ReviewImportCard";
import { SignOffCard } from "./SignOffCard";
import type { CardProps, CardStatus } from "./types";

type RenderProps = { args: unknown; status: unknown; respond?: (answer: never) => unknown; result?: string };

/** A card as a CopilotKit render function. */
function asCard<Args, Answer>(Card: ComponentType<CardProps<Args, Answer>>) {
  return function render({ args, status, respond, result }: RenderProps) {
    const answer = respond as ((value: Answer) => unknown) | undefined;
    return (
      <Card
        args={args as Partial<Args>}
        status={String(status) as CardStatus}
        respond={answer ? (value) => void answer(value) : undefined}
        result={result}
      />
    );
  };
}

const NEVER_CALL = "Never call this yourself.";

export function useGates() {
  useHumanInTheLoop<ConfirmStepArgs>({
    name: "confirm_step",
    description:
      "Ask the user to confirm that the current framework step is complete before moving to " +
      "the next one. Call it only when the step's questions are answered and recorded. " +
      "step: the current step number. summary: a short summary of what the step established. " +
      'The answer is {"approved": true} or {"approved": false, "missing": "<what the user says is missing>"}.',
    parameters: z.object({ step: z.number().int().min(1).max(5), summary: z.string() }),
    render: asCard(ConfirmStepCard),
  });
  useHumanInTheLoop<{ gaps: CardGap[] }>({
    name: "decide_gaps",
    description: `The app asks the user to answer or accept each open gap from the design review. ${NEVER_CALL}`,
    parameters: z.object({
      gaps: z.array(
        z.object({
          id: z.string(),
          lens: z.string(),
          severity: z.string(),
          item_ids: z.array(z.string()),
          risk: z.string(),
          decision_needed: z.string(),
        }),
      ),
    }),
    render: asCard(DecideGapsCard),
  });
  useHumanInTheLoop<{ candidates: CardCandidate[] }>({
    name: "review_import",
    description: `The app asks the user to accept, edit or reject each item found in their attached files. ${NEVER_CALL}`,
    parameters: z.object({ candidates: z.array(z.any()) }),
    render: asCard(ReviewImportCard),
  });
  useHumanInTheLoop<{ prd: PrdDoc }>({
    name: "sign_off_prd",
    description: `The app asks the user to sign off PRD v1.0 or reject it with a reason. ${NEVER_CALL}`,
    parameters: z.object({ prd: z.any() }),
    render: asCard(SignOffCard),
  });
}
