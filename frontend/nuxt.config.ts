export default defineNuxtConfig({
  ssr: false,
  modules: ["@nuxtjs/tailwindcss"],

  css: ["~/assets/css/main.css"],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8000",
    },
  },

  devServer: {
    port: 3000,
  },

  app: {
    head: {
      title: "EmbedForge",
      meta: [
        { name: "description", content: "Agentic AI for Embedded C Code Generation" },
      ],
      link: [
        { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
      ],
    },
  },

  compatibilityDate: "2024-07-01",
});
