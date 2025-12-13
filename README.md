# Controle de Gastos — Django Templates

## Url: [https://construtora-gastos.onrender.com](https://construtora-gastos.onrender.com)

## Visão Geral

O **Controle de Gastos** é uma aplicação web desenvolvida em **Django**, utilizando **Django Templates** para a camada de apresentação, com o objetivo de auxiliar usuários no gerenciamento financeiro pessoal. O sistema permite acompanhar despesas, receitas, cartões de crédito, categorias, locais de gastos e projeções futuras, oferecendo uma visão clara e organizada da situação financeira mensal.

A aplicação foi pensada para uso individual, com dados isolados por usuário, oferecendo recursos de filtragem e visualização histórica para facilitar a tomada de decisões financeiras.

---

## Funcionalidades Principais

### 📊 Dashboard Mensal

* Listagem das **despesas do mês atual**
* Exibição do **saldo atual**
* Cálculo do **total gasto**
* Cálculo do **total recebido**
* Exibição da **fatura atual dos cartões de crédito**
* Opção de **visualizar meses anteriores**

---

### 💸 Despesas

* Cadastro, edição e exclusão de despesas
* Associação de despesas a:

  * Categorias
  * Lugares
  * Cartões de crédito (quando aplicável)
* Filtros avançados para localizar valores específicos
* Visualização mensal das despesas

---

### 💰 Receitas

* Listagem das **receitas financeiras** (dinheiro recebido)
* Controle mensal de receitas
* Integração com o cálculo de saldo e totais

---

### 🏷️ Categorias

* Cadastro e gerenciamento de **categorias personalizadas**
* Visualização do **total gasto por mês em cada categoria**
* Facilita a análise de onde o dinheiro está sendo gasto

---

### 📍 Lugares

* Cadastro de **lugares personalizados** (ex: mercado, restaurante, aluguel)
* Listagem de gastos por lugar
* Visualização mensal dos gastos em cada local

---

### 💳 Cartões de Crédito

* Cadastro de múltiplos **cartões de crédito**
* Associação de despesas aos cartões
* Exibição da:

  * **Fatura atual**
  * **Parcelas restantes** para cada despesa
* Controle claro de gastos parcelados

---

### ⏳ Despesas Previstas

* Cadastro de **despesas futuras**
* Permite antecipar gastos e planejar o orçamento
* Separação clara entre despesas atuais e previstas

---

### 👤 Usuário e Perfil

* Sistema de **autenticação de usuários**
* Cadastro e edição de **perfil do usuário**
* Dados financeiros isolados por conta

---

### 🔎 Filtros e Pesquisa

* Filtros disponíveis em diversas páginas
* Possibilidade de buscar por:

  * Valores
  * Datas
  * Categorias
  * Lugares
  * Cartões

---

## Tecnologias Utilizadas

* **Python**
* **Django**
* **Django Templates**
* **HTML5**
* **Tailwind CSS**
* **PostgreSQL** 
* **Banco e Projeto em Deploy no Render**
* **SendGrid para envio de emails**
* **UptimeRobot para manter o sistema ativo 24h**

---

## Objetivo do Projeto

O projeto tem como objetivo fornecer uma ferramenta simples, intuitiva e eficiente para **controle financeiro pessoal**, permitindo que o usuário acompanhe sua vida financeira de forma organizada, com histórico mensal, detalhamento de gastos e projeções futuras.

---

## Status do Projeto

🚧 Em desenvolvimento contínuo — novas funcionalidades e melhorias visuais estão sendo adicionadas.

---

## Autor

Desenvolvido por **Natan Ayres do Nascimento**.
