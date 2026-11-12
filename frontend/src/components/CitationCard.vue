<script setup lang="ts">
import { ArrowUpRight, ChevronDown, FileText } from "@lucide/vue";
import type { Citation } from "../api";
import { accessDate, officialUrl } from "../format";

defineProps<{ citation: Citation }>();
</script>

<template>
  <details :id="`citacao-${citation.id}`" class="citation-card">
    <summary>
      <span class="citation-number">{{ citation.id }}</span>
      <span class="citation-heading"
        ><strong>{{ citation.title }}</strong
        ><span>{{ citation.section }}</span></span
      >
      <ChevronDown :size="17" class="details-chevron" aria-hidden="true" />
    </summary>
    <div class="citation-content">
      <span class="eyebrow"
        ><FileText :size="13" aria-hidden="true" /> TRECHO CONSULTADO</span
      >
      <blockquote>{{ citation.quote }}</blockquote>
      <p class="fine-print">{{ citation.legal_validity }}</p>
      <div class="citation-bottom">
        <span>Consultado em {{ accessDate(citation.accessed_at) }}</span>
        <a
          v-if="officialUrl(citation.url)"
          :href="officialUrl(citation.url)"
          target="_blank"
          rel="noopener noreferrer"
          >Abrir documento <ArrowUpRight :size="15" aria-hidden="true"
        /></a>
      </div>
    </div>
  </details>
</template>
