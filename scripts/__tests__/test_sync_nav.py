"""Regression tests for scripts/sync-nav.py (issue #172, quality-gate score 48).

Pure python, no kiro-cli: translate_titles is patched to identity and
REPO_ROOT is pointed at a throwaway tree of empty placeholder files (only
existence matters to sync-nav).

    python3 -m unittest scripts/__tests__/test_sync_nav.py
    python3 -m pytest scripts/__tests__/test_sync_nav.py
"""
import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "sync_nav", Path(__file__).resolve().parents[1] / "sync-nav.py")
sync_nav = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sync_nav)


def _dedent(s):
    return textwrap.dedent(s).lstrip("\n")


class SyncNavCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._orig_root = sync_nav.REPO_ROOT
        self._orig_translate = sync_nav.translate_titles
        sync_nav.REPO_ROOT = self.root
        self.translate_calls = []

        def identity(titles, lang):
            self.translate_calls.append(list(titles))
            return list(titles)
        sync_nav.translate_titles = identity

    def tearDown(self):
        sync_nav.REPO_ROOT = self._orig_root
        sync_nav.translate_titles = self._orig_translate
        self._tmp.cleanup()

    def make_repo(self, en_summary, dst_summary, files, lang="cn", en_readme=None, dst_readme=None):
        (self.root / "en").mkdir()
        (self.root / lang).mkdir()
        (self.root / "en" / "SUMMARY.md").write_text(_dedent(en_summary), encoding="utf-8")
        (self.root / lang / "SUMMARY.md").write_text(_dedent(dst_summary), encoding="utf-8")
        if en_readme is not None:
            (self.root / "en" / "README.md").write_text(_dedent(en_readme), encoding="utf-8")
        if dst_readme is not None:
            (self.root / lang / "README.md").write_text(_dedent(dst_readme), encoding="utf-8")
        for f in files:
            p = self.root / lang / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()

    def dst(self, lang="cn", name="SUMMARY.md"):
        return (self.root / lang / name).read_text(encoding="utf-8")


class SubtreeEndTests(unittest.TestCase):
    def test_stops_at_next_heading_and_excludes_trailing_blank(self):
        text = "* [A](a.md)\n  * [A1](a1.md)\n\n## Next\n\n* [B](b.md)\n"
        start = len("* [A](a.md)\n")
        end = sync_nav._subtree_end(text, start, 0)
        self.assertEqual(text[:end], "* [A](a.md)\n  * [A1](a1.md)\n")

    def test_no_descendants_returns_start_pos(self):
        text = "* [A](a.md)\n* [B](b.md)\n"
        start = len("* [A](a.md)\n")
        self.assertEqual(sync_nav._subtree_end(text, start, 0), start)

    def test_no_descendants_before_heading_returns_start_pos(self):
        text = "* [A](a.md)\n\n## Next\n\n* [B](b.md)\n"
        start = len("* [A](a.md)\n")
        self.assertEqual(sync_nav._subtree_end(text, start, 0), start)

    def test_stops_at_sibling_at_same_indent(self):
        text = "  * [A](a.md)\n    * [A1](a1.md)\n  * [B](b.md)\n"
        start = len("  * [A](a.md)\n")
        end = sync_nav._subtree_end(text, start, 2)
        self.assertEqual(text[:end], "  * [A](a.md)\n    * [A1](a1.md)\n")


class Issue172Tests(SyncNavCase):
    EN = """
        # Table of contents

        ## Operations Guide

        * [Operations Guide](ops/README.md)
          * [Infrastructure Setup](ops/01-infrastructure-setup.md)
          * [Troubleshooting Playbook](ops/16-troubleshooting-playbook.md)

        ## Observability

        * [Observability Overview](observability/README.md)
          * [Metrics](observability/metrics/README.md)

        ## Quiz Collection

        * Platform Engineering
          * [Helm Quiz](quizzes/platform-engineering/01-helm-quiz.md)
        * Operations Guide
          * [Infrastructure Setup Quiz](quizzes/ops/01-infrastructure-setup-quiz.md)
          * [Troubleshooting Playbook Quiz](quizzes/ops/16-troubleshooting-playbook-quiz.md)
        """
    CN = """
        # 目录

        ## 运维指南

        * [运维指南](ops/README.md)
          * [基础设施设置](ops/01-infrastructure-setup.md)

        ## 可观测性

        * [可观测性概览](observability/README.md)
          * [指标](observability/metrics/README.md)

        ## 测验合集

        * 平台工程
          * [Helm 测验](quizzes/platform-engineering/01-helm-quiz.md)
        * 运维指南
          * [基础设施设置测验](quizzes/ops/01-infrastructure-setup-quiz.md)
        """
    FILES = [
        "ops/README.md", "ops/01-infrastructure-setup.md", "ops/16-troubleshooting-playbook.md",
        "observability/README.md", "observability/metrics/README.md",
        "quizzes/platform-engineering/01-helm-quiz.md",
        "quizzes/ops/01-infrastructure-setup-quiz.md", "quizzes/ops/16-troubleshooting-playbook-quiz.md",
    ]

    def run_ops(self, heading_map):
        self.make_repo(self.EN, self.CN, self.FILES)
        sync_nav.sync_summary("ops", "cn", heading_map)
        return self.dst()

    def test_new_last_child_stays_under_its_own_heading(self):
        """Defect 1: ops/16 used to be spliced under '## 可观测性'."""
        out = self.run_ops({"Operations Guide": {"cn": "运维指南"}, "Observability": {"cn": "可观测性"},
                            "Quiz Collection": {"cn": "测验合集"}})
        self.assertIn(_dedent("""
            * [运维指南](ops/README.md)
              * [基础设施设置](ops/01-infrastructure-setup.md)
              * [Troubleshooting Playbook](ops/16-troubleshooting-playbook.md)

            ## 可观测性

            * [可观测性概览](observability/README.md)
            """), out)
        self.assertNotIn("## 可观测性\n\n  * [Troubleshooting Playbook]", out)

    def test_heading_drift_reuses_block_holding_present_paths_and_repairs_map(self):
        """Defect 2: map said 测验集合, file says 测验合集 -> used to append a
        duplicate '## 测验集合' block re-listing every quiz."""
        heading_map = {"Operations Guide": {"cn": "运维指南"}, "Observability": {"cn": "可观测性"},
                       "Quiz Collection": {"cn": "测验集合"}}
        out = self.run_ops(heading_map)
        self.assertEqual(out.count("## 测验"), 1)
        self.assertNotIn("测验集合", out)
        self.assertEqual(heading_map["Quiz Collection"]["cn"], "测验合集")
        self.assertEqual(out.count("quizzes/ops/01-infrastructure-setup-quiz.md"), 1)
        self.assertNotIn(["Quiz Collection"], self.translate_calls)

    def test_pathless_group_with_present_child_is_not_re_emitted(self):
        """Defect 3: '* Operations Guide' (path None) used to be rendered as a
        brand-new untranslated group with the single new quiz under it."""
        out = self.run_ops({"Operations Guide": {"cn": "运维指南"}, "Observability": {"cn": "可观测性"},
                            "Quiz Collection": {"cn": "测验合集"}})
        self.assertNotIn("* Operations Guide\n", out)
        self.assertNotIn("* Platform Engineering\n", out)
        self.assertTrue(out.endswith(_dedent("""
            * 运维指南
              * [基础设施设置测验](quizzes/ops/01-infrastructure-setup-quiz.md)
              * [Troubleshooting Playbook Quiz](quizzes/ops/16-troubleshooting-playbook-quiz.md)
            """)), out)

    def test_rerun_is_idempotent(self):
        heading_map = {"Operations Guide": {"cn": "运维指南"}, "Observability": {"cn": "可观测性"},
                       "Quiz Collection": {"cn": "测验集合"}}
        first = self.run_ops(heading_map)
        sync_nav.sync_summary("ops", "cn", heading_map)
        self.assertEqual(self.dst(), first)

    def test_brand_new_heading_is_still_appended(self):
        """A heading the locale has never had (no present paths) keeps the
        old behaviour: a new block at EOF using the cached translation."""
        self.make_repo(self.EN, self.CN, self.FILES + ["storage/README.md"])
        en = (self.root / "en" / "SUMMARY.md").read_text(encoding="utf-8")
        (self.root / "en" / "SUMMARY.md").write_text(
            en + "\n## Storage\n\n* [Storage Overview](storage/README.md)\n", encoding="utf-8")
        heading_map = {"Storage": {"cn": "存储"}}
        sync_nav.sync_summary("storage", "cn", heading_map)
        self.assertTrue(self.dst().endswith("\n## 存储\n\n* [Storage Overview](storage/README.md)\n"))


class LegacySplitBlockTests(SyncNavCase):
    def test_anchors_beside_present_siblings_without_repairing_map(self):
        """en folded autoscaling/ under 'Kubernetes Core Concepts'; the locale
        still has a separate legacy block for it. The new page goes beside its
        existing siblings, and the map is NOT rewritten to point 'Kubernetes
        Core Concepts' at the legacy block."""
        en = """
            ## Kubernetes Core Concepts

            * [Cluster Architecture](core/01-cluster-architecture.md)
            * Autoscaling
              * [KEDA](autoscaling/01-keda.md)
              * [Karpenter](autoscaling/02-karpenter.md)
            """
        jp = """
            ## Kubernetes のコアコンセプト

            * [クラスターアーキテクチャ](core/01-cluster-architecture.md)

            ## オートスケーリング

            * [KEDA](autoscaling/01-keda.md)
            """
        self.make_repo(en, jp, ["core/01-cluster-architecture.md", "autoscaling/01-keda.md",
                                "autoscaling/02-karpenter.md"], lang="jp")
        heading_map = {"Kubernetes Core Concepts": {"jp": "Kubernetes の中核概念"}}
        sync_nav.sync_summary("autoscaling", "jp", heading_map)
        out = self.dst("jp")
        self.assertEqual(out.count("## "), 2)
        self.assertLess(out.index("## オートスケーリング"), out.index("autoscaling/02-karpenter.md"))
        self.assertEqual(heading_map["Kubernetes Core Concepts"]["jp"], "Kubernetes の中核概念")


class ReadmeTocTests(SyncNavCase):
    def test_toc_heading_resolved_by_content_not_translation(self):
        """sync_readme's '## Table of Contents' lookup was map-only (and the map
        never had the key), so a first-ever section sync could fall through to
        appending after '## License'. Also covers the body scan of the LAST
        '### ' ToC block stopping at the next '## ' heading."""
        en_readme = """
            # Docs

            ## Table of Contents

            ### Linux & Container
            1. [Linux Basics](./basics/01-linux-basics.md) | [Quiz](./quizzes/basics/01-linux-basics-quiz.md)

            ### Storage
            1. [Storage Overview](./storage/README.md)

            ## License

            MIT
            """
        cn_readme = """
            # 文档

            ## 目录

            ### 基础
            1. [Linux 基础](./basics/01-linux-basics.md) | [测验](./quizzes/basics/01-linux-basics-quiz.md)

            ## 许可证

            MIT
            """
        self.make_repo("", "", ["basics/01-linux-basics.md", "quizzes/basics/01-linux-basics-quiz.md",
                                "storage/README.md"], en_readme=en_readme, dst_readme=cn_readme)
        heading_map = {"Storage": {"cn": "存储"}}
        sync_nav.sync_readme("storage", "cn", heading_map)
        out = self.dst(name="README.md")
        self.assertIn("### 存储\n1. [Storage Overview](./storage/README.md)\n\n## 许可证", out)
        self.assertEqual(out.count("## License"), 0)
        self.assertEqual(heading_map["Table of Contents"]["cn"], "目录")
        self.assertNotIn(["Table of Contents"], self.translate_calls)


class ReadmeIncrementalTests(SyncNavCase):
    """Issue #179 (networking backfill, score 82): a section whose README ToC
    block was copied by an earlier backfill never received the pages en
    gained afterwards -- sync_readme() returned on seeing the first path."""
    EN = """
        # Docs

        ## Table of Contents

        ### Networking
        1. [Networking Overview](./networking/README.md) | [Quiz](./quizzes/networking/00-networking-overview-quiz.md)
        2. [Network Fundamentals](./basics/06-network-fundamentals-part1.md)
        3. [VPC CNI](./networking/01-vpc-cni.md) | [Quiz](./quizzes/networking/01-vpc-cni-quiz.md)
        4. **Calico Deep Dive**
           - [Calico Introduction](./networking/calico/README.md)
           - [Part 9: Operations](./networking/calico/09-operations.md) | [Quiz](./quizzes/networking/calico/09-operations-quiz.md)
           - [Part 10: Upgrades](./networking/calico/10-upgrades.md) | [Quiz](./quizzes/networking/calico/10-upgrades-quiz.md)
        5. [Gateway API](./networking/04-gateway-api.md) | [Quiz](./quizzes/networking/04-gateway-api-quiz.md)
        6. [Cross-Org VPC Connectivity](./networking/05-cross-org-vpc-connectivity.md) | [Quiz](./quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
        7. [Pod Network Benchmark](./networking/06-pod-network-benchmark.md) | [Quiz](./quizzes/networking/06-pod-network-benchmark-quiz.md)

        ### Service Mesh
        1. [Istio](./service-mesh/02-istio.md)

        ## License

        MIT
        """
    CN = """
        # 文档

        ## 目录

        ### 网络
        1. [网络概览](./networking/README.md) | [测验](./quizzes/networking/00-networking-overview-quiz.md)
        2. [VPC CNI](./networking/01-vpc-cni.md) | [测验](./quizzes/networking/01-vpc-cni-quiz.md)
        3. **Calico 深入解析**
           - [Calico 简介](./networking/calico/README.md)
           - [第 9 部分：运维](./networking/calico/09-operations.md) | [测验](./quizzes/networking/calico/09-operations-quiz.md)
        4. [Gateway API](./networking/04-gateway-api.md) | [测验](./quizzes/networking/04-gateway-api-quiz.md)
        5. [仅本地保留的页面](./networking/99-local-only.md)

        ### Service Mesh
        1. [Istio](./service-mesh/02-istio.md)

        ## 许可证

        MIT
        """
    FILES = [
        "networking/README.md", "quizzes/networking/00-networking-overview-quiz.md",
        "networking/01-vpc-cni.md", "quizzes/networking/01-vpc-cni-quiz.md",
        "networking/calico/README.md",
        "networking/calico/09-operations.md", "quizzes/networking/calico/09-operations-quiz.md",
        "networking/calico/10-upgrades.md", "quizzes/networking/calico/10-upgrades-quiz.md",
        "networking/04-gateway-api.md", "quizzes/networking/04-gateway-api-quiz.md",
        "networking/05-cross-org-vpc-connectivity.md",
        "quizzes/networking/05-cross-org-vpc-connectivity-quiz.md",
        "networking/06-pod-network-benchmark.md",  # its quiz is NOT translated yet
        "networking/99-local-only.md",
        "service-mesh/02-istio.md",
    ]

    def run_networking(self, heading_map=None):
        self.make_repo("", "", self.FILES, en_readme=self.EN, dst_readme=self.CN)
        sync_nav.sync_readme("networking", "cn", heading_map if heading_map is not None else {})
        return self.dst(name="README.md")

    def test_new_pages_are_spliced_in_en_order_and_renumbered(self):
        out = self.run_networking()
        self.assertIn(_dedent("""
            ### 网络
            1. [网络概览](./networking/README.md) | [测验](./quizzes/networking/00-networking-overview-quiz.md)
            2. [VPC CNI](./networking/01-vpc-cni.md) | [测验](./quizzes/networking/01-vpc-cni-quiz.md)
            3. **Calico 深入解析**
               - [Calico 简介](./networking/calico/README.md)
               - [第 9 部分：运维](./networking/calico/09-operations.md) | [测验](./quizzes/networking/calico/09-operations-quiz.md)
               - [Part 10: Upgrades](./networking/calico/10-upgrades.md) | [测验](./quizzes/networking/calico/10-upgrades-quiz.md)
            4. [Gateway API](./networking/04-gateway-api.md) | [测验](./quizzes/networking/04-gateway-api-quiz.md)
            5. [Cross-Org VPC Connectivity](./networking/05-cross-org-vpc-connectivity.md) | [测验](./quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
            6. [Pod Network Benchmark](./networking/06-pod-network-benchmark.md)
            7. [仅本地保留的页面](./networking/99-local-only.md)

            ### Service Mesh
            1. [Istio](./service-mesh/02-istio.md)

            ## 许可证
            """), out)
        # untranslated page (no cn/basics/06-...) is not added; nothing duplicated
        self.assertNotIn("06-network-fundamentals", out)
        self.assertEqual(out.count("### 网络"), 1)
        self.assertEqual(out.count("networking/01-vpc-cni.md"), 1)
        self.assertEqual(out.count("**Calico"), 1)
        # spliced lines reuse the block's own quiz label, not en's "Quiz"
        self.assertNotIn("[Quiz](", out)

    def test_only_new_titles_are_translated(self):
        self.run_networking()
        self.assertEqual(self.translate_calls,
                         [["Part 10: Upgrades", "Cross-Org VPC Connectivity", "Pod Network Benchmark"]])

    def test_rerun_is_idempotent_and_silent(self):
        first = self.run_networking()
        self.translate_calls.clear()
        sync_nav.sync_readme("networking", "cn", {})
        self.assertEqual(self.dst(name="README.md"), first)
        self.assertEqual(self.translate_calls, [])

    def test_new_group_with_children_lands_after_its_predecessor(self):
        pad = " " * 8  # self.EN is dedented by make_repo; keep the inserted lines aligned
        en = self.EN.replace(
            f"{pad}5. [Gateway API]",
            f"{pad}5. **Cilium Deep Dive**\n{pad}   - [Cilium Introduction](./networking/cilium/README.md)\n"
            f"{pad}   - [Part 1: Introduction](./networking/cilium/01-introduction.md)\n{pad}6. [Gateway API]")
        self.make_repo("", "", self.FILES + ["networking/cilium/README.md", "networking/cilium/01-introduction.md"],
                       en_readme=en, dst_readme=self.CN)
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn(_dedent("""
               - [Part 10: Upgrades](./networking/calico/10-upgrades.md) | [测验](./quizzes/networking/calico/10-upgrades-quiz.md)
            4. **Cilium Deep Dive**
               - [Cilium Introduction](./networking/cilium/README.md)
               - [Part 1: Introduction](./networking/cilium/01-introduction.md)
            5. [Gateway API](./networking/04-gateway-api.md) | [测验](./quizzes/networking/04-gateway-api-quiz.md)
            """), out)
        self.assertEqual(out.count("**Cilium Deep Dive**"), 1)

    def test_first_ever_sync_still_copies_whole_block(self):
        cn = self.CN.replace("### 网络", "### 占位").replace("networking/", "placeholder/")
        self.make_repo("", "", self.FILES, en_readme=self.EN, dst_readme=cn)
        heading_map = {"Networking": {"cn": "网络"}}
        sync_nav.sync_readme("networking", "cn", heading_map)
        out = self.dst(name="README.md")
        self.assertIn("### 网络\n1. [Networking Overview](./networking/README.md)", out)
        self.assertIn("7. [Pod Network Benchmark](./networking/06-pod-network-benchmark.md)\n", out)
        self.assertNotIn("06-network-fundamentals", out)


if __name__ == "__main__":
    unittest.main()
