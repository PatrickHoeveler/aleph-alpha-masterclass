export enum UsecaseQaAnswerStatus {
  PENDING = 'pending',
  FAILED = 'failed',
  SUCCESSFUL = 'successful',
}

export type UsecaseQaAnswer = {
  traceId?: string
  answer?: string
  status: UsecaseQaAnswerStatus
  sql_statement?: string
  sql_harmless?: boolean
  explanation?: string
}

export interface BaseQaChatEntry {
  questionId: string
  question: string
  timestamp: Date
}

export interface UsecaseQaDocumentChatEntry extends BaseQaChatEntry {
  answer: UsecaseQaAnswer
}

export interface UsecaseQaDocumentIndexChatEntry extends BaseQaChatEntry {
  namespace: string
  collection: string
  answer: UsecaseQaAnswer
}

export type UsecaseQaChatEntry = UsecaseQaDocumentChatEntry | UsecaseQaDocumentIndexChatEntry

export type UsecaseQaChatInitializationEntry =
  | Omit<UsecaseQaDocumentChatEntry, 'questionId' | 'timestamp' | 'answer'>
  | Omit<UsecaseQaDocumentIndexChatEntry, 'questionId' | 'timestamp' | 'answer'>
