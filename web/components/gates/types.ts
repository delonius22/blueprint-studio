// The props every approval card takes (SPECS S11.4): its tool call's arguments, where the call
// is, how to answer it, and the answer once given.
export type CardStatus = "inProgress" | "executing" | "complete";

export type CardProps<Args, Answer> = {
  args: Partial<Args>;
  status: CardStatus;
  respond?: (answer: Answer) => void;
  result?: string;
};
