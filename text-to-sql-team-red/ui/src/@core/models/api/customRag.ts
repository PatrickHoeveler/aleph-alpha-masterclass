import { z } from 'zod'

export interface CustomRagRequest {
  question: string
}

export const CUSTOM_RAG_RESPONSE_SCHEMA = z.object({
  sql_statement: z.string(),
  sql_harmless: z.boolean(),
  explanation: z.string(),

})

export type CustomRagResponse = z.infer<typeof CUSTOM_RAG_RESPONSE_SCHEMA>
