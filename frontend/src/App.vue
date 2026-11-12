<script setup lang="ts">
import { computed, KeepAlive, onMounted, onUnmounted, ref } from "vue";
import {
  ArrowUpRight,
  BookOpen,
  Calculator,
  ChevronRight,
  Layers,
  MessageSquare,
  RefreshCw,
} from "@lucide/vue";
import { api, type Health, type SourceInventory } from "./api";
import AssistantView from "./views/AssistantView.vue";
import SimulatorView from "./views/SimulatorView.vue";
import SourcesView from "./views/SourcesView.vue";

type View = "assistente" | "simulador" | "fontes";
const navigation = [
  {
    id: "assistente" as const,
    label: "Assistente",
    caption: "Pergunte e confira",
    icon: MessageSquare,
  },
  {
    id: "simulador" as const,
    label: "Simulador",
    caption: "Explore hipóteses",
    icon: Calculator,
  },
  {
    id: "fontes" as const,
    label: "Fontes",
    caption: "Documentos e cobertura",
    icon: BookOpen,
  },
];
function readView(): View {
  const hash = window.location.hash.slice(1);
  return hash === "simulador" || hash === "fontes" ? hash : "assistente";
}
function focusMain() {
  document.getElementById("main-content")?.focus();
}
const view = ref<View>(readView());
const current = computed(() =>
  navigation.find((item) => item.id === view.value)!,
);
const health = ref<Health | null>(null);
const connection = ref<"checking" | "online" | "offline">("checking");
const inventory = ref<SourceInventory | null>(null);
const sourcesLoading = ref(false);
const sourcesError = ref("");
const controller = new AbortController();

function navigate(next: View) {
  view.value = next;
  window.location.hash = next;
  window.scrollTo({ top: 0, behavior: "instant" });
}
const updateView = () => {
  view.value = readView();
};
async function checkHealth() {
  connection.value = "checking";
  try {
    health.value = await api.health(controller.signal);
    connection.value = "online";
  } catch {
    health.value = null;
    connection.value = "offline";
  }
}
async function loadSources() {
  if (sourcesLoading.value) return;
  sourcesLoading.value = true;
  sourcesError.value = "";
  try {
    inventory.value = await api.sources(controller.signal);
  } catch (cause) {
    sourcesError.value =
      cause instanceof Error
        ? cause.message
        : "Não foi possível carregar os documentos.";
  } finally {
    sourcesLoading.value = false;
  }
}
onMounted(() => {
  window.addEventListener("hashchange", updateView);
  void checkHealth();
  void loadSources();
});
onUnmounted(() => {
  controller.abort();
  window.removeEventListener("hashchange", updateView);
});
</script>

<template>
  <a class="skip-link" href="#main-content" @click.prevent="focusMain"
    >Pular para o conteúdo</a
  >
  <div class="app-shell">
    <aside class="sidebar">
      <a
        class="brand"
        href="#assistente"
        aria-label="TaxMind AI, início"
        @click="navigate('assistente')"
        ><span class="brand-mark"
          ><Layers :size="24" :stroke-width="1.7" aria-hidden="true" /></span
        ><span>taxmind<span class="brand-ai">AI</span></span></a
      >
      <span class="sidebar-label">SEU ESPAÇO PARA ENTENDER</span>
      <nav aria-label="Navegação principal">
        <a
          v-for="item in navigation"
          :key="item.id"
          :href="`#${item.id}`"
          class="nav-item"
          :class="{ active: view === item.id }"
          :aria-current="view === item.id ? 'page' : undefined"
          @click="navigate(item.id)"
          ><component
            :is="item.icon"
            :size="20"
            :stroke-width="1.7"
            aria-hidden="true" /><span
            ><strong>{{ item.label }}</strong
            ><small>{{ item.caption }}</small></span
          ><ChevronRight :size="14" class="nav-chevron" aria-hidden="true"
        /></a>
      </nav>
      <div class="sidebar-bottom">
        <div class="sidebar-note">
          <span class="note-dot"></span
          ><strong>Clareza começa<br />com uma boa fonte.</strong>
          <p>Explore. Pergunte. Confira.</p>
        </div>
        <a
          href="https://github.com/clarak-dev/taxmind-ai"
          target="_blank"
          rel="noopener noreferrer"
          class="project-link"
          >Sobre o projeto <ArrowUpRight :size="15" aria-hidden="true" /></a
        ><span class="sidebar-footnote">Projeto educacional independente</span>
      </div>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <div class="breadcrumb">
          <span>Explorar</span
          ><ChevronRight :size="13" aria-hidden="true" /><strong>{{
            current.label
          }}</strong>
        </div>
        <button
          class="connection-badge"
          :class="connection"
          type="button"
          :disabled="connection === 'checking'"
          :aria-busy="connection === 'checking'"
          aria-label="Verificar conexão com o serviço"
          @click="checkHealth"
        >
          <span class="status-dot"></span
          ><span>{{
            connection === "online"
              ? "Serviço conectado"
              : connection === "checking"
                ? "Verificando serviço"
                : "Sem conexão com o serviço"
          }}</span
          ><RefreshCw
            :size="12"
            :class="{ spin: connection === 'checking' }"
            aria-hidden="true"
          />
        </button>
      </header>
      <main id="main-content" class="main-content" tabindex="-1">
        <KeepAlive>
          <AssistantView
            v-if="view === 'assistente'"
            :inventory="inventory"
            :sources-loading="sourcesLoading"
            :sources-error="sourcesError"
            :configured="health ? health.rag_status === 'configured' : null"
            @navigate="navigate"
          /><SimulatorView v-else-if="view === 'simulador'" /><SourcesView
            v-else
            :inventory="inventory"
            :loading="sourcesLoading"
            :error="sourcesError"
            @reload="loadSources"
          />
        </KeepAlive>
      </main>
      <footer class="page-footer">
        <span
          >TaxMind AI <span class="footer-dot">·</span> Tecnologia para entender
          melhor.</span
        ><span>Conteúdo educacional. Confira sempre as fontes.</span>
      </footer>
    </div>
  </div>
</template>
