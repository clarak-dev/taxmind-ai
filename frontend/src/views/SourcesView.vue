<script setup lang="ts">
import { ArrowUpRight, BookOpen, FileText, Info, RefreshCw } from "@lucide/vue";
import type { SourceInventory } from "../api";
import { accessDate, officialUrl, publisher, sourceLabel } from "../format";

defineProps<{
  inventory: SourceInventory | null;
  loading: boolean;
  error: string;
}>();
defineEmits<{ reload: [] }>();
</script>

<template>
  <section class="page-intro">
    <span class="eyebrow"
      ><span class="mini-line"></span> CONTEXTO PARA CONFIAR E CONFERIR</span
    >
    <h1>
      Conheça as fontes.<br />Entenda os limites<span class="accent-dot"
        >.</span
      >
    </h1>
    <p>
      Saiba quais documentos estão disponíveis para consulta<br
        class="desktop-break"
      />
      e até onde vai a cobertura desta versão.
    </p>
  </section>
  <div class="sources-layout">
    <section class="sources-main" aria-labelledby="documents-title">
      <div class="section-heading">
        <h2 id="documents-title">Documentos oficiais</h2>
        <button
          class="text-button"
          :disabled="loading"
          @click="$emit('reload')"
        >
          <RefreshCw :size="14" :class="{ spin: loading }" aria-hidden="true" />
          Atualizar lista
        </button>
      </div>
      <p v-if="loading" class="surface source-loading" role="status">
        Carregando documentos e cobertura…
      </p>
      <div v-else-if="error" class="notice notice-error" role="alert">
        <Info :size="19" aria-hidden="true" />
        <p>{{ error }}</p>
      </div>
      <template v-else-if="inventory"
        ><article
          v-for="(source, index) in inventory.sources"
          :key="source.id"
          class="source-document surface"
        >
          <div class="source-document-top">
            <span class="document-order">0{{ index + 1 }}</span
            ><span
              class="subtle-badge"
              :class="{ 'badge-muted': source.indexed_chunks === 0 }"
              >{{
                source.indexed_chunks > 0
                  ? "Disponível para consulta"
                  : "Ainda fora da consulta"
              }}</span
            >
          </div>
          <span class="eyebrow">{{ publisher(source.id) }}</span>
          <h3>{{ sourceLabel(source.id, source.title) }}</h3>
          <p class="document-full-title">{{ source.title }}</p>
          <div class="document-scope">
            <BookOpen :size="17" aria-hidden="true" />
            <p v-if="inventory.scope.sources[source.id]?.articles">
              Artigos disponíveis:
              {{ inventory.scope.sources[source.id]?.articles?.join(", ") }}. Os
              demais artigos e remissões não estão incluídos neste recorte.
            </p>
            <p v-else>
              Página selecionada para consulta. O conteúdo reflete a versão
              coletada e pode ter atualizações posteriores.
            </p>
          </div>
          <p class="fine-print">{{ source.legal_validity }}</p>
          <div class="source-document-bottom">
            <span>{{
              source.accessed_at
                ? `Coletado em ${accessDate(source.accessed_at)}`
                : "Coleta ainda não realizada"
            }}</span
            ><a
              v-if="officialUrl(source.url)"
              class="document-link"
              :href="officialUrl(source.url)"
              target="_blank"
              rel="noopener noreferrer"
              >Abrir fonte oficial <ArrowUpRight :size="16" aria-hidden="true"
            /></a>
          </div></article
      ></template>
    </section>
    <aside class="sources-aside">
      <section class="coverage-card">
        <span class="icon-tile"
          ><FileText :size="21" aria-hidden="true"
        /></span>
        <h2>O que entra na consulta?</h2>
        <p>
          Conceitos gerais e dispositivos selecionados da reforma tributária do
          consumo.
        </p>
        <hr />
        <h3>O que pode ficar de fora?</h3>
        <ul>
          <li>Artigos não incluídos no recorte.</li>
          <li>Exceções e atos publicados depois da coleta.</li>
          <li>Informações específicas de uma empresa ou pessoa.</li>
        </ul>
        <p class="coverage-note">
          A data de coleta não define a vigência de uma regra. Confira sempre o
          documento e seus efeitos no período da sua dúvida.
        </p>
      </section>
      <div
        v-if="inventory && inventory.index_status !== 'validated'"
        class="notice notice-warm"
        role="status"
      >
        <Info :size="19" aria-hidden="true" />
        <p>
          O conteúdo ainda não está pronto para consulta nesta instância. Você
          pode abrir as fontes oficiais diretamente.
        </p>
      </div>
    </aside>
  </div>
</template>
