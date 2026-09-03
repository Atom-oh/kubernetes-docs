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


class ReadmeSpliceEdgeTests(SyncNavCase):
    """Cases an adversarial review of the #179 fix produced: emptied groups,
    a group's new first child, locale-only nested lines, a parent and child
    sharing one path, en cross-links, 0-based lists, chrome fallback."""
    EN, CN, FILES = ReadmeIncrementalTests.EN, ReadmeIncrementalTests.CN, ReadmeIncrementalTests.FILES
    PAD = " " * 8  # self.EN/self.CN are dedented by make_repo; keep inserted lines aligned
    CILIUM_GROUP = (f"{PAD}6. **Cilium Deep Dive**\n{PAD}   - [Cilium Introduction](./networking/cilium/README.md)\n"
                    f"{PAD}   - [Part 1: Introduction](./networking/cilium/01-introduction.md)\n{PAD}7. [Cross-Org VPC")
    CILIUM_FILES = ["networking/cilium/README.md", "networking/cilium/01-introduction.md"]

    def test_group_whose_children_all_failed_to_translate_is_not_emitted(self):
        """A label followed by a NEW top-level page used to be judged new via
        that page (the next linked line anywhere) and land as a dangling
        '**Cilium Deep Dive**' with nothing under it."""
        en = self.EN.replace(f"{self.PAD}6. [Cross-Org VPC", self.CILIUM_GROUP)
        self.make_repo("", "", self.FILES, en_readme=en, dst_readme=self.CN)  # no cn/networking/cilium/*
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertNotIn("Cilium", out)
        self.assertIn("5. [Cross-Org VPC Connectivity]", out)

    def test_retry_after_failed_group_children_inserts_label_once(self):
        en = self.EN.replace(f"{self.PAD}6. [Cross-Org VPC", self.CILIUM_GROUP)
        self.make_repo("", "", self.FILES, en_readme=en, dst_readme=self.CN)
        sync_nav.sync_readme("networking", "cn", {})
        for f in self.CILIUM_FILES:  # the retry run: translate.sh succeeded this time
            (self.root / "cn" / f).parent.mkdir(parents=True, exist_ok=True)
            (self.root / "cn" / f).touch()
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn(_dedent("""
            4. [Gateway API](./networking/04-gateway-api.md) | [测验](./quizzes/networking/04-gateway-api-quiz.md)
            5. **Cilium Deep Dive**
               - [Cilium Introduction](./networking/cilium/README.md)
               - [Part 1: Introduction](./networking/cilium/01-introduction.md)
            6. [Cross-Org VPC Connectivity]"""), out)
        self.assertEqual(out.count("**Cilium Deep Dive**"), 1)

    def test_new_first_child_goes_under_the_existing_group_label(self):
        """The label used to be judged new by its FIRST child alone, so a new
        first child re-emitted '**Calico Deep Dive**' (untranslated) above the
        locale's own '**Calico 深入解析**'."""
        en = self.EN.replace(
            f"{self.PAD}   - [Calico Introduction]",
            f"{self.PAD}   - [Part 0: Concepts](./networking/calico/00-concepts.md)\n{self.PAD}   - [Calico Introduction]")
        self.make_repo("", "", self.FILES + ["networking/calico/00-concepts.md"], en_readme=en, dst_readme=self.CN)
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn(_dedent("""
            3. **Calico 深入解析**
               - [Part 0: Concepts](./networking/calico/00-concepts.md)
               - [Calico 简介](./networking/calico/README.md)
            """), out)
        self.assertEqual(out.count("**Calico"), 1)
        self.assertNotIn("Calico Deep Dive", out)

    def test_locale_only_nested_lines_stay_under_their_parent(self):
        cn = self.CN.replace(
            f"{self.PAD}5. [仅本地保留的页面]",
            f"{self.PAD}   - [仅本地子页面](./networking/04a-local-child.md)\n{self.PAD}5. [仅本地保留的页面]")
        self.make_repo("", "", self.FILES + ["networking/04a-local-child.md"], en_readme=self.EN, dst_readme=cn)
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn(_dedent("""
            4. [Gateway API](./networking/04-gateway-api.md) | [测验](./quizzes/networking/04-gateway-api-quiz.md)
               - [仅本地子页面](./networking/04a-local-child.md)
            5. [Cross-Org VPC Connectivity]"""), out)

    def test_new_sibling_after_a_child_sharing_its_parents_path_follows_the_child(self):
        """en's 'Network Fundamentals' parent and its 'Part 1' child link the
        same file; a new 'Part 2' after 'Part 1' used to anchor on the parent
        (first match) and land above 'Part 1'."""
        en = self.EN.replace(
            f"{self.PAD}2. [Network Fundamentals](./basics/06-network-fundamentals-part1.md)\n",
            f"{self.PAD}2. [Network Fundamentals](./basics/06-network-fundamentals-part1.md)\n"
            f"{self.PAD}   - [Part 1](./basics/06-network-fundamentals-part1.md)\n"
            f"{self.PAD}   - [Part 2](./basics/06-network-fundamentals-part2.md)\n")
        cn = self.CN.replace(
            f"{self.PAD}2. [VPC CNI]",
            f"{self.PAD}2. [网络基础](./basics/06-network-fundamentals-part1.md)\n"
            f"{self.PAD}   - [第 1 部分](./basics/06-network-fundamentals-part1.md)\n{self.PAD}2. [VPC CNI]")
        self.make_repo("", "", self.FILES + ["basics/06-network-fundamentals-part1.md",
                                             "basics/06-network-fundamentals-part2.md"],
                       en_readme=en, dst_readme=cn)
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn(_dedent("""
            2. [网络基础](./basics/06-network-fundamentals-part1.md)
               - [第 1 部分](./basics/06-network-fundamentals-part1.md)
               - [Part 2](./basics/06-network-fundamentals-part2.md)
            3. [VPC CNI]"""), out)

    def test_cross_linked_page_in_another_block_does_not_hijack_the_splice(self):
        """en lists one SageMaker page under both Data Pipeline and AI/ML. A
        locale that only has the AI/ML block must get a NEW Data Pipeline
        block, not the Kafka pages spliced into AI/ML."""
        en = """
            ## Table of Contents

            ### Data Pipeline
            1. [SageMaker Domains](./data-on-eks/sagemaker/01-domains.md)
            2. [Kafka on EKS](./data-on-eks/kafka/README.md)

            ### AI/ML
            1. [Bedrock](./ai-ml/01-bedrock.md)
            2. [SageMaker Domains](./data-on-eks/sagemaker/01-domains.md)

            ## License
            """
        cn = """
            ## 目录

            ### 人工智能/机器学习
            1. [Bedrock](./ai-ml/01-bedrock.md)
            2. [SageMaker 域](./data-on-eks/sagemaker/01-domains.md)

            ## 许可证
            """
        self.make_repo("", "", ["data-on-eks/sagemaker/01-domains.md", "data-on-eks/kafka/README.md",
                                "ai-ml/01-bedrock.md"], en_readme=en, dst_readme=cn)
        sync_nav.sync_readme("data-on-eks", "cn", {"Data Pipeline": {"cn": "数据管道"}})
        out = self.dst(name="README.md")
        self.assertIn(_dedent("""
            ### 人工智能/机器学习
            1. [Bedrock](./ai-ml/01-bedrock.md)
            2. [SageMaker 域](./data-on-eks/sagemaker/01-domains.md)

            ### 数据管道
            1. [SageMaker Domains](./data-on-eks/sagemaker/01-domains.md)
            2. [Kafka on EKS](./data-on-eks/kafka/README.md)

            ## 许可证
            """), out)

    def test_zero_based_block_keeps_its_numbering(self):
        en = """
            ## Table of Contents

            ### Platform Engineering
            0. [Platform Engineering Overview](./platform-engineering/README.md)
            1. [Helm](./platform-engineering/01-helm.md)
            2. [Backstage](./platform-engineering/02-backstage.md)

            ## License
            """
        cn = """
            ## 目录

            ### 平台工程
            0. [平台工程概览](./platform-engineering/README.md)
            1. [Helm](./platform-engineering/01-helm.md)

            ## 许可证
            """
        self.make_repo("", "", ["platform-engineering/README.md", "platform-engineering/01-helm.md",
                                "platform-engineering/02-backstage.md"], en_readme=en, dst_readme=cn)
        sync_nav.sync_readme("platform-engineering", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn("0. [平台工程概览](./platform-engineering/README.md)\n1. [Helm](./platform-engineering/01-helm.md)\n"
                      "2. [Backstage](./platform-engineering/02-backstage.md)\n", out)

    def test_lab_label_falls_back_to_the_files_wording_when_the_block_has_none(self):
        en = self.EN.replace(
            "7. [Pod Network Benchmark](./networking/06-pod-network-benchmark.md) | [Quiz](./quizzes/networking/06-pod-network-benchmark-quiz.md)",
            "7. [Pod Network Benchmark](./networking/06-pod-network-benchmark.md) | [Lab](./labs/networking/06-pod-network-benchmark-lab.md)")
        cn = self.CN.replace(
            f"{self.PAD}### 网络\n",
            f"{self.PAD}### 基础\n{self.PAD}1. [Linux 基础](./basics/01-linux-basics.md) | [实验](./labs/basics/01-linux-basics-lab.md)\n\n{self.PAD}### 网络\n")
        self.make_repo("", "", self.FILES + ["labs/networking/06-pod-network-benchmark-lab.md",
                                             "basics/01-linux-basics.md", "labs/basics/01-linux-basics-lab.md"],
                       en_readme=en, dst_readme=cn)
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn("6. [Pod Network Benchmark](./networking/06-pod-network-benchmark.md) | [实验](./labs/networking/06-pod-network-benchmark-lab.md)\n", out)
        self.assertNotIn("[Lab](", out)

    def test_section_with_nothing_translated_leaves_readme_unchanged(self):
        """An empty '### <heading>' block has no paths to be recognized by, so
        it used to be appended again on every run."""
        cn = self.CN.replace("### 网络", "### 占位").replace("networking/", "placeholder/")
        self.make_repo("", "", ["service-mesh/02-istio.md"], en_readme=self.EN, dst_readme=cn)
        before = self.dst(name="README.md")
        sync_nav.sync_readme("networking", "cn", {"Networking": {"cn": "网络"}})
        sync_nav.sync_readme("networking", "cn", {"Networking": {"cn": "网络"}})
        self.assertEqual(self.dst(name="README.md"), before)
        self.assertEqual(self.translate_calls, [])

    def test_new_group_label_is_translated_in_the_same_batch_as_its_children(self):
        """The locales carry '**Calico 深入解析**', so a new group's label must
        not land as English '**Cilium Deep Dive**' between translated lines."""
        sync_nav.translate_titles = lambda titles, lang: [f"<{lang}:{t}>" for t in titles]
        en = self.EN.replace(f"{self.PAD}6. [Cross-Org VPC", self.CILIUM_GROUP)
        self.make_repo("", "", self.FILES + self.CILIUM_FILES, en_readme=en, dst_readme=self.CN)
        sync_nav.sync_readme("networking", "cn", {})
        out = self.dst(name="README.md")
        self.assertIn(_dedent("""
            5. **<cn:Cilium Deep Dive>**
               - [<cn:Cilium Introduction>](./networking/cilium/README.md)
               - [<cn:Part 1: Introduction>](./networking/cilium/01-introduction.md)
            6. [<cn:Cross-Org VPC Connectivity>]"""), out)
        self.assertNotIn("Cilium Deep Dive**", out.replace("<cn:Cilium Deep Dive>", ""))

    def test_first_sync_borrows_the_files_quiz_wording(self):
        cn = self.CN.replace("### 网络", "### 占位").replace("networking/", "placeholder/")
        self.make_repo("", "", self.FILES, en_readme=self.EN, dst_readme=cn)
        sync_nav.sync_readme("networking", "cn", {"Networking": {"cn": "网络"}})
        out = self.dst(name="README.md")
        self.assertIn("1. [Networking Overview](./networking/README.md) | [测验](./quizzes/networking/00-networking-overview-quiz.md)\n", out)
        self.assertNotIn("[Quiz](", out)


if __name__ == "__main__":
    unittest.main()
