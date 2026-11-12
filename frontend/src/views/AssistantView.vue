<script setup lang="ts">
import { nextTick, onUnmounted, ref } from "vue";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ChevronRight,
  FileText,
  Info,
  LoaderCircle,
  MessageSquare,
  ShieldCheck,
} from "@lucide/vue";
import { api, type Answer, type SourceInventory } from "../api";
import { officialUrl, publisher, sourceLabel } from "../format";
import CitationCard from "../components/CitationCard.vue";

defineProps<{
  inventory: SourceInventory | null;
  sourcesLoading: boolean;
  sourcesError: string;
  configured: boolean | null;
}>();
const emit = defineEmits<{ navigate: [view: "fontes"] }>();
const question = ref("");
const textarea = ref<HTMLTextAreaElement>();
const pending = ref(false);
const error = ref("");
const result = ref<Answer | null>(null);
let controller: AbortController | undefined;
onUnmounted(() => controller?.abort());

const suggestions = [
  {
    label: "Conheça a CBS",
    question: "O que é a CBS e de quem é sua competência?",
  },
  {
    label: "Entenda o IBS",
    question: "O que é o IBS e de quem é sua competência?",
  },
  {
    label: "Princípio da neutralidade",
    question:
      "O que o princípio da neutralidade procura evitar nas decisões de consumo?",
  },
];

async function choose(value: string) {
  question.value = value;
  await nextTick();
  textarea.value?.focus();
}

async function submit() {
  const value = question.value.trim();
  if (pending.value || value.length < 3 || value.length > 500) return;
  error.value = "";
  result.value = null;
  pending.value = true;
  controller = new AbortController();
  try {
    result.value = await api.ask(value, controller.signal);
  } catch (cause) {
    error.value =
      cause instanceof Error
        ? cause.message
        : "Não foi possível concluir a consulta.";
  } finally {
    pending.value = false;
  }
}

function showCitation(id: number) {
  const element = document.getElementById(
    `citacao-${id}`,
  ) as HTMLDetailsElement | null;
  if (!element) return;
  element.open = true;
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  element.querySelector("summary")?.focus({ preventScroll: true });
}
</script>

<template>
  <section class="page-intro">
    <span class="eyebrow"
      ><span class="mini-line"></span> REFORMA TRIBUTÁRIA DO CONSUMO</span
    >
    <h1>
      Mais clareza para<br />entender a reforma<span class="accent-dot">.</span>
    </h1>
    <p>
      Uma dúvida de cada vez. Respostas em linguagem simples,<br
        class="desktop-break"
      />
      com os documentos oficiais sempre por perto.
    </p>
  </section>

  <div class="workspace-grid">
    <div class="primary-column">
      <div v-if="configured === false" class="notice notice-warm" role="status">
        <Info :size="19" aria-hidden="true" />
        <p>
          O assistente está indisponível no momento. Você ainda pode explorar as
          fontes e o simulador.
        </p>
      </div>
      <form class="question-card" :aria-busy="pending" @submit.prevent="submit">
        <div class="card-heading">
          <span class="icon-tile"
            ><MessageSquare :size="20" aria-hidden="true"
          /></span>
          <div>
            <span class="eyebrow">ASSISTENTE TAXMIND</span>
            <h2><label for="question">Qual é a sua dúvida?</label></h2>
          </div>
        </div>
        <textarea
          id="question"
          ref="textarea"
          v-model="question"
          maxlength="500"
          minlength="3"
          required
          rows="4"
          :disabled="pending"
          placeholder="Por exemplo: o que muda com a criação da CBS?"
          aria-describedby="question-help question-count"
          @keydown.ctrl.enter.prevent="submit"
          @keydown.meta.enter.prevent="submit"
        ></textarea>
        <div class="composer-bottom">
          <span id="question-count" class="character-count"
            >{{ question.length }} / 500</span
          ><button
            class="button button-primary"
            type="submit"
            :disabled="pending || question.trim().length < 3"
          >
            <LoaderCircle
              v-if="pending"
              :size="17"
              class="spin"
              aria-hidden="true"
            /><span>{{
              pending ? "Consultando…" : "Consultar documentos"
            }}</span
            ><ArrowRight v-if="!pending" :size="17" aria-hidden="true" />
          </button>
        </div>
        <p id="question-help" class="privacy-note">
          <ShieldCheck :size="14" aria-hidden="true" /> A pergunta é processada
          por um serviço de IA. Não inclua dados pessoais ou empresariais.
        </p>
      </form>

      <section
        v-if="!result && !pending && !error"
        class="suggestions"
        aria-labelledby="suggestions-title"
      >
        <h3 id="suggestions-title">Um ponto de partida</h3>
        <div class="suggestion-grid">
          <button
            v-for="(item, index) in suggestions"
            :key="item.label"
            type="button"
            class="suggestion-card"
            @click="choose(item.question)"
          >
            <span class="suggestion-index">0{{ index + 1 }}</span
            ><span>{{ item.label }}</span
            ><ArrowUpRight :size="17" aria-hidden="true" />
          </button>
        </div>
      </section>

      <div
        v-if="pending"
        class="response-loading"
        role="status"
        aria-live="polite"
      >
        <span class="loading-orbit"
          ><LoaderCircle :size="23" class="spin" aria-hidden="true"
        /></span>
        <div>
          <strong>Consultando os documentos</strong>
          <p>A resposta pode levar alguns instantes.</p>
        </div>
      </div>
      <div v-if="error" class="notice notice-error" role="alert">
        <Info :size="20" aria-hidden="true" />
        <div>
          <strong>Não foi possível concluir a consulta</strong>
          <p>{{ error }}</p>
          <button class="text-button" @click="submit">
            Tentar novamente <ArrowRight :size="15" aria-hidden="true" />
          </button>
        </div>
      </div>

      <section
        v-if="result?.status === 'abstained'"
        class="abstention-card"
        aria-live="polite"
      >
        <span class="icon-tile warm"
          ><BookOpen :size="23" aria-hidden="true"
        /></span>
        <h2>A evidência ainda não é suficiente</h2>
        <p>{{ result.answer }}</p>
        <p class="muted">
          Tente uma pergunta mais específica ou confira quais documentos estão
          disponíveis.
        </p>
        <button class="text-button" @click="emit('navigate', 'fontes')">
          Ver fontes e cobertura <ArrowRight :size="16" aria-hidden="true" />
        </button>
      </section>

      <section
        v-if="result?.status === 'answered'"
        class="answer-section"
        aria-live="polite"
        aria-labelledby="answer-title"
      >
        <div class="section-heading">
          <h2 id="answer-title">Sua resposta</h2>
          <span class="subtle-badge"
            ><FileText :size="13" aria-hidden="true" /> Com referências</span
          >
        </div>
        <div class="answer-card">
          <span class="eyebrow">VOCÊ PERGUNTOU</span>
          <p class="asked-question">{{ result.question }}</p>
          <div class="answer-text">
            <p v-for="(claim, index) in result.claims" :key="index">
              {{ claim.text }}
              <button
                v-for="id in claim.citation_ids"
                :key="id"
                type="button"
                class="citation-jump"
                :aria-label="`Ver fonte ${id}`"
                @click="showCitation(id)"
              >
                [{{ id }}]
              </button>
            </p>
          </div>
          <p class="answer-caution">
            <Info :size="15" aria-hidden="true" /> Explicação educacional.
            Confira o contexto, a vigência e as exceções nas fontes.
          </p>
        </div>
        <h3 class="references-title">Confira de onde veio</h3>
        <CitationCard
          v-for="citation in result.citations"
          :key="citation.id"
          :citation="citation"
        />
      </section>

      <div class="method-strip">
        <div><span>01</span><strong>Você pergunta</strong></div>
        <ChevronRight :size="14" aria-hidden="true" />
        <div><span>02</span><strong>Os documentos dão contexto</strong></div>
        <ChevronRight :size="14" aria-hidden="true" />
        <div><span>03</span><strong>Você confere a fonte</strong></div>
      </div>
    </div>

    <aside class="context-column" aria-label="Documentos e limites da consulta">
      <section class="reading-card">
        <div class="aside-heading">
          <BookOpen :size="19" aria-hidden="true" />
          <h2>Fontes para conferir.</h2>
        </div>
        <p>Conheça os documentos que dão base às consultas.</p>
        <div v-if="sourcesLoading" class="source-skeleton" role="status">
          Carregando documentos…
        </div>
        <p v-else-if="sourcesError" class="fine-print">
          Não foi possível carregar as fontes agora.
        </p>
        <div v-else-if="inventory" class="reading-list">
          <a
            v-for="source in inventory.sources"
            :key="source.id"
            :href="officialUrl(source.url)"
            target="_blank"
            rel="noopener noreferrer"
            ><span class="document-icon"
              ><FileText :size="17" aria-hidden="true" /></span
            ><span
              ><small>{{ publisher(source.id) }}</small
              ><strong>{{ sourceLabel(source.id, source.title) }}</strong></span
            ><ArrowUpRight :size="16" aria-hidden="true"
          /></a>
        </div>
        <button class="text-button" @click="emit('navigate', 'fontes')">
          Explorar as fontes <ArrowRight :size="15" aria-hidden="true" />
        </button>
      </section>
      <section class="scope-card">
        <span class="eyebrow">TRANSPARÊNCIA DESDE O INÍCIO</span>
        <h3>Um recorte.<br />Limites à vista.</h3>
        <p>
          A consulta cobre documentos e artigos selecionados. Uma pergunta pode
          exigir informações que ainda não estão disponíveis.
        </p>
        <button class="text-button" @click="emit('navigate', 'fontes')">
          Entender a cobertura
          <ArrowUpRight :size="15" aria-hidden="true" /></button
        ><span class="scope-decoration" aria-hidden="true">+</span>
      </section>
    </aside>
  </div>
</template>
