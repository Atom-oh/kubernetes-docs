---
head:
  - - script
    - {}
    - |
      (function () {
        var lang = (navigator.language || navigator.userLanguage || '').toLowerCase();
        var target = '/kubernetes-docs/en/';
        if (lang.indexOf('ko') === 0) target = '/kubernetes-docs/ko/';
        else if (lang.indexOf('zh') === 0) target = '/kubernetes-docs/cn/';
        else if (lang.indexOf('ja') === 0) target = '/kubernetes-docs/jp/';
        else if (lang.indexOf('es') === 0) target = '/kubernetes-docs/es/';
        location.replace(target);
      })();
---

# Kubernetes & Amazon EKS Training Content

언어를 선택하세요 / Select your language / 选择语言 / 言語を選択 / Seleccione idioma:

- [한국어 (Korean)](./ko/)
- [English](./en/)
- [中文 (Chinese)](./cn/)
- [日本語 (Japanese)](./jp/)
- [Español (Spanish)](./es/)
