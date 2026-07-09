---
head:
  - - script
    - {}
    - |
      (function () {
        var lang = (navigator.language || navigator.userLanguage || '').toLowerCase();
        var target = lang.indexOf('ko') === 0 ? '/kubernetes-docs/ko/' : '/kubernetes-docs/en/';
        location.replace(target);
      })();
---

# Kubernetes & Amazon EKS Training Content

언어를 선택하세요 / Select your language:

- [한국어 (Korean)](./ko/)
- [English](./en/)
