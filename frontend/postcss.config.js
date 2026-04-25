/**
 * PostCSS 配置
 *
 * PostCSS 是什么？
 *   CSS 的后处理器。它本身不做任何事，但可以通过插件做很多事。
 *   这里用两个插件：
 *   1. tailwindcss - 把 Tailwind 的 class 编译成实际 CSS
 *   2. autoprefixer - 自动添加浏览器前缀（如 -webkit-、-moz-），兼容不同浏览器
 */
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
