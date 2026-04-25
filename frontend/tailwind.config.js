/**
 * Tailwind CSS 配置
 *
 * Tailwind 是什么？
 *   原子化 CSS 框架。不用写单独的 CSS 文件，
 *   直接在 HTML 中用 class 名组合样式。
 *   例如：className="bg-blue-500 text-white rounded-lg p-4"
 *   等价于写了一段 CSS：background: blue; color: white; border-radius: 8px; padding: 16px;
 *
 * content 配置：
 *   告诉 Tailwind 扫描哪些文件来提取 class 名。
 *   只有被扫描到的 class 才会打包到最终 CSS 中（ Tree Shaking 机制）。
 */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
