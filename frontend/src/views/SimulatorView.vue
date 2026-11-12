<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from "vue";
import {
  ArrowRight,
  Calculator,
  ChevronDown,
  Info,
  LoaderCircle,
  SlidersHorizontal,
} from "@lucide/vue";
import { api, type Simulation } from "../api";
import { decimalInput, money, percent } from "../format";

const fields = reactive({ amount: "100,00", first: "10", second: "15" });
const touched = ref(false);
const pending = ref(false);
const error = ref("");
const result = ref<Simulation | null>(null);
let controller: AbortController | undefined;
onUnmounted(() => controller?.abort());

const parsed = computed(() => ({
  base_amount: decimalInput(fields.amount, 2, 1_000_000_000_000),
  current_rate_percent: decimalInput(fields.first, 4, 100),
  proposed_rate_percent: decimalInput(fields.second, 4, 100),
}));
const valid = computed(() =>
  Object.values(parsed.value).every((value) => value !== null),
);
const changed = computed(
  () =>
    result.value &&
    (Number(parsed.value.base_amount) !== Number(result.value.base_amount) ||
      Number(parsed.value.current_rate_percent) !==
        Number(result.value.current.rate_percent) ||
      Number(parsed.value.proposed_rate_percent) !==
        Number(result.value.proposed.rate_percent) ||
      !valid.value),
);

async function submit() {
  touched.value = true;
  if (!valid.value || pending.value) return;
  const { base_amount, current_rate_percent, proposed_rate_percent } =
    parsed.value;
  if (
    base_amount === null ||
    current_rate_percent === null ||
    proposed_rate_percent === null
  )
    return;
  pending.value = true;
  error.value = "";
  result.value = null;
  controller = new AbortController();
  try {
    result.value = await api.simulate(
      { base_amount, current_rate_percent, proposed_rate_percent },
      controller.signal,
    );
  } catch (cause) {
    error.value =
      cause instanceof Error
        ? cause.message
        : "Não foi possível calcular os cenários.";
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <section class="page-intro">
    <span class="eyebrow"
      ><span class="mini-line"></span> EXPLORE SUAS HIPÓTESES</span
    >
    <h1>
      Dois cenários.<br />Uma comparação clara<span class="accent-dot">.</span>
    </h1>
    <p>
      Escolha um valor e duas taxas para entender a diferença.<br
        class="desktop-break"
      />
      Todos os parâmetros são informados por você.
    </p>
  </section>

  <div class="simulation-grid">
    <form
      class="simulation-form surface"
      :aria-busy="pending"
      @submit.prevent="submit"
    >
      <div class="card-heading">
        <span class="icon-tile"
          ><SlidersHorizontal :size="20" aria-hidden="true"
        /></span>
        <div>
          <span class="eyebrow">SEUS PARÂMETROS</span>
          <h2>Defina os cenários</h2>
        </div>
      </div>
      <span class="hypothesis-label"
        >Exemplo hipotético · valores editáveis</span
      >
      <div class="form-field">
        <label for="base-amount">Valor sem tributo</label>
        <div class="input-wrap">
          <span>R$</span
          ><input
            id="base-amount"
            v-model="fields.amount"
            inputmode="decimal"
            type="text"
            required
            :disabled="pending"
            :aria-invalid="touched && parsed.base_amount === null"
            aria-describedby="amount-help"
          />
        </div>
        <small id="amount-help"
          >Use até duas casas decimais, sem separador de milhares.</small
        ><span v-if="touched && parsed.base_amount === null" class="field-error"
          >Informe um valor entre zero e 1 trilhão, com até duas casas
          decimais.</span
        >
      </div>
      <div class="rates-grid">
        <div class="form-field">
          <label for="rate-first">Taxa do cenário A</label>
          <div class="input-wrap rate-a">
            <input
              id="rate-first"
              v-model="fields.first"
              inputmode="decimal"
              type="text"
              required
              :disabled="pending"
              :aria-invalid="touched && parsed.current_rate_percent === null"
              aria-describedby="rates-help"
            /><span>%</span>
          </div>
          <span
            v-if="touched && parsed.current_rate_percent === null"
            class="field-error"
            >Use uma taxa de 0 a 100, com até quatro casas decimais.</span
          >
        </div>
        <div class="form-field">
          <label for="rate-second">Taxa do cenário B</label>
          <div class="input-wrap rate-b">
            <input
              id="rate-second"
              v-model="fields.second"
              inputmode="decimal"
              type="text"
              required
              :disabled="pending"
              :aria-invalid="touched && parsed.proposed_rate_percent === null"
              aria-describedby="rates-help"
            /><span>%</span>
          </div>
          <span
            v-if="touched && parsed.proposed_rate_percent === null"
            class="field-error"
            >Use uma taxa de 0 a 100, com até quatro casas decimais.</span
          >
        </div>
      </div>
      <p id="rates-help" class="fine-print rates-help">
        As taxas são hipóteses suas. Não são alíquotas oficiais.
      </p>
      <button
        class="button button-primary full-width"
        type="submit"
        :disabled="pending"
      >
        <LoaderCircle
          v-if="pending"
          :size="17"
          class="spin"
          aria-hidden="true"
        />{{ pending ? "Calculando…" : "Comparar cenários"
        }}<ArrowRight v-if="!pending" :size="17" aria-hidden="true" />
      </button>
    </form>

    <div class="simulation-output" aria-live="polite">
      <div v-if="error" class="notice notice-error" role="alert">
        <Info :size="20" aria-hidden="true" />
        <p>{{ error }}</p>
      </div>
      <section v-if="result" class="simulation-result surface">
        <div class="section-heading">
          <h2>Sua comparação</h2>
          <span class="subtle-badge">Cenário hipotético</span>
        </div>
        <p class="muted">
          Sobre a mesma base de {{ money(result.base_amount) }}.
        </p>
        <p v-if="changed" class="notice-inline">
          Você alterou os parâmetros. Compare novamente para atualizar os
          valores abaixo.
        </p>
        <div class="scenario-pair">
          <div class="scenario scenario-a">
            <span class="scenario-label"><i></i> CENÁRIO A</span
            ><strong class="scenario-rate">{{
              percent(result.current.rate_percent)
            }}</strong>
            <dl>
              <div>
                <dt>Tributo</dt>
                <dd>{{ money(result.current.tax_amount) }}</dd>
              </div>
              <div class="scenario-total">
                <dt>Total com tributo</dt>
                <dd>{{ money(result.current.total_amount) }}</dd>
              </div>
            </dl>
          </div>
          <div class="scenario scenario-b">
            <span class="scenario-label"><i></i> CENÁRIO B</span
            ><strong class="scenario-rate">{{
              percent(result.proposed.rate_percent)
            }}</strong>
            <dl>
              <div>
                <dt>Tributo</dt>
                <dd>{{ money(result.proposed.tax_amount) }}</dd>
              </div>
              <div class="scenario-total">
                <dt>Total com tributo</dt>
                <dd>{{ money(result.proposed.total_amount) }}</dd>
              </div>
            </dl>
          </div>
        </div>
        <div class="difference">
          <span>Diferença de tributo entre B e A</span
          ><strong>{{ money(result.tax_difference) }}</strong>
        </div>
        <details class="calculation-details">
          <summary>
            Como o cálculo funciona
            <ChevronDown :size="16" aria-hidden="true" />
          </summary>
          <p>Tributo = valor sem tributo × taxa ÷ 100.</p>
          <p>Total = valor sem tributo + tributo, arredondado para centavos.</p>
          <p>
            Uma diferença negativa indica que o tributo do cenário B é menor.
          </p>
        </details>
      </section>
      <section v-else-if="!error" class="simulation-empty surface">
        <span class="simulation-art" aria-hidden="true"
          ><Calculator :size="43" :stroke-width="1.25" /></span
        ><span class="eyebrow">A COMPARAÇÃO COMEÇA AQUI</span>
        <h2>Transforme hipóteses<br />em números.</h2>
        <p>
          Preencha os campos e compare os valores de cada cenário, com a conta à
          vista.
        </p>
      </section>
      <div class="notice educational-note">
        <Info :size="19" aria-hidden="true" />
        <p>
          Esta comparação é educacional e não determina a carga tributária real.
          Não considera créditos, regimes especiais, transição ou incidência por
          produto.
        </p>
      </div>
    </div>
  </div>
</template>
