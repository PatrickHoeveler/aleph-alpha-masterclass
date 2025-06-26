<script lang="ts" setup>
import { ref } from 'vue'
import UsecaseQaAnswerActions from './UsecaseQaAnswerActions.vue'
import SkeletonPlaceholderContainer from '@/@core/components/SkeletonPlaceholderContainer.vue'
import { UsecaseQaAnswerStatus, type UsecaseQaChatEntry } from '@/models/UsecaseQaChatEntry'
import { AaText, AaButton } from '@aleph-alpha/ds-components-vue'
import { HTTP_CLIENT } from '@/utils/http'
import { marked } from 'marked'

const props = defineProps<{
  chatEntry: UsecaseQaChatEntry
}>()

const sqlResult = ref<string | null>(null)
const sqlResultTable = ref<string | null>(null)
const executing = ref(false)

interface SqlResult {
  headers: string[];
  rows: unknown[][];
}

async function executeSql() {
  if (!props.chatEntry.answer.sql_statement) return
  executing.value = true
  sqlResult.value = null
  sqlResultTable.value = null
  try {
    const response = await HTTP_CLIENT.post('execute-sql', {
      body: { sql_statement: props.chatEntry.answer.sql_statement },
    })
    sqlResult.value = JSON.stringify(response.data, null, 2)
    // Parse and convert to markdown table
    const data = response.data as SqlResult
    if (data && data.headers && data.rows) {
      let md = '| ' + data.headers.join(' | ') + ' |\n'
      md += '| ' + data.headers.map(() => '---').join(' | ') + ' |\n'
      for (const row of data.rows) {
        md += '| ' + row.map((cell: unknown) => cell === null ? '' : String(cell)).join(' | ') + ' |\n'
      }
      sqlResultTable.value = md
    }
  } catch (err: any) {
    sqlResult.value = err?.response?.data?.detail || err.message || 'Execution failed.'
    sqlResultTable.value = null
  } finally {
    executing.value = false
  }
}
</script>

<template>
  <div class="w-179 p-M gap-XS text-core-content-primary flex grow rounded">
    <div
      class="border-core-border-default flex size-8 flex-shrink-0 items-center justify-center rounded-full border"
    >
      <span class="i-aa-logo flex size-4 flex-shrink-0" />
    </div>
    <SkeletonPlaceholderContainer
      v-if="chatEntry.answer.status === UsecaseQaAnswerStatus.PENDING"
      :bar-count="4"
      :bar-height-px="32"
      class="gap-y-lg"
    />
    <div v-else class="flex w-full flex-col justify-center">
      <AaText element="div" class="whitespace-pre-line">
        <template v-if="chatEntry.answer.sql_statement">
          <strong>SQL Statement:</strong>
          <pre>{{ chatEntry.answer.sql_statement }}</pre>
          <template v-if="chatEntry.answer.sql_harmless">
            <AaButton
              class="shrink-0 mt-2"
              size="small"
              variant="primary"
              :loading="executing"
              @click="executeSql"
            >
              {{ executing ? 'Executing...' : 'Execute SQL' }}
            </AaButton>
          </template>
        </template>
        <template v-if="chatEntry.answer.sql_harmless !== undefined">
          <strong>SQL Harmless:</strong>
          <span :style="{ color: chatEntry.answer.sql_harmless ? 'green' : 'red' }">
            {{ chatEntry.answer.sql_harmless ? 'Yes' : 'No' }}
          </span>
          &nbsp;
        </template>
        <template v-if="chatEntry.answer.explanation">
          <strong>Explanation:</strong>
          <div>{{ chatEntry.answer.explanation }}</div>
        </template>
        <template v-if="!chatEntry.answer.sql_statement && !chatEntry.answer.explanation">
          {{ chatEntry.answer.answer || 'No answer found' }}
        </template>
      </AaText>
      <div v-if="sqlResultTable" class="mt-4 p-2 border rounded bg-gray-50 overflow-auto">
        <strong>SQL Result:</strong>
        <div style="overflow-x:auto">
          <pre v-if="!sqlResultTable">{{ sqlResult }}</pre>
          <div v-else v-html="marked(sqlResultTable)"></div>
        </div>
      </div>
      <div v-else-if="sqlResult" class="mt-4 p-2 border rounded bg-gray-50">
        <strong>SQL Result:</strong>
        <pre>{{ sqlResult }}</pre>
      </div>
      <div class="pt-L text-core-content-tertiary flex items-center justify-between">
        <UsecaseQaAnswerActions :chat-entry="chatEntry" />
      </div>
    </div>
  </div>
</template>
