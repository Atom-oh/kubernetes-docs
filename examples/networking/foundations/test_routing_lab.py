import subprocess
import unittest
from unittest.mock import patch

from routing_lab import (Docker, LabError, Resources, ROUTER_LEFT, SERVER, SOCKET,
                         check_subnets, traceroute_reaches_expected_hops)


class FakeDocker:
    def __init__(self, fail_start=False, fail_second_network=False, fail_remove=False):
        self.objects = {"user-network", "user-container"}
        self.calls = []
        self.next_id = 0
        self.network_count = 0
        self.fail_start = fail_start
        self.fail_second_network = fail_second_network
        self.fail_remove = fail_remove

    def call(self, *args, check=True):
        self.calls.append(args)
        if args[:2] == ("network", "create"):
            self.network_count += 1
            if self.fail_second_network and self.network_count == 2:
                raise LabError("Simulated pool allocation failure")
        if args[:2] == ("network", "create") or args[0] == "create":
            self.next_id += 1
            identifier = f"created-id-{self.next_id}"
            self.objects.add(identifier)
            return subprocess.CompletedProcess(args, 0, identifier + "\n", "")
        if args[0] == "start" and self.fail_start:
            raise LabError("Simulated container start failure")
        if args[0] == "rm" or args[:2] == ("network", "rm"):
            if self.fail_remove and args[0] == "rm":
                return subprocess.CompletedProcess(args, 1, "", "Simulated removal failure")
            self.objects.remove(args[-1])
        return subprocess.CompletedProcess(args, 0, "", "")


class ResourceOwnershipTests(unittest.TestCase):
    def test_failed_start_still_removes_created_container_and_preserves_user_objects(self):
        docker = FakeDocker(fail_start=True)
        with self.assertRaisesRegex(LabError, "start failure"):
            with Resources(docker) as owned:
                network = owned.network("lesson-net", "192.0.2.0/29", "lesson=id")
                owned.container("lesson-client", network, "192.0.2.2", "lesson=id")
        self.assertEqual(docker.objects, {"user-network", "user-container"})
        deletes = [a for a in docker.calls if a[0] == "rm" or a[:2] == ("network", "rm")]
        self.assertTrue(all(a[-1].startswith("created-id-") for a in deletes))
        self.assertEqual(deletes[0][0], "rm")  # Remove attached containers before networks.

    def test_partial_network_setup_only_removes_successfully_created_ids(self):
        docker = FakeDocker(fail_second_network=True)
        with self.assertRaisesRegex(LabError, "allocation failure"):
            with Resources(docker) as owned:
                owned.network("left", "192.0.2.0/29", "lesson=id")
                owned.network("right", "198.51.100.0/29", "lesson=id")
        self.assertEqual(docker.objects, {"user-network", "user-container"})

    def test_cleanup_failure_cannot_be_reported_as_success(self):
        docker = FakeDocker(fail_remove=True)
        with self.assertRaisesRegex(LabError, "Cleanup incomplete"):
            with Resources(docker) as owned:
                network = owned.network("lesson-net", "192.0.2.0/29", "lesson=id")
                owned.container("lesson-client", network, "192.0.2.2", "lesson=id")
        self.assertIn("user-container", docker.objects)
        self.assertIn("user-network", docker.objects)

    def test_nondefault_host_route_collision_is_rejected(self):
        with self.assertRaisesRegex(LabError, "overlaps"):
            check_subnets([{"dst": "192.0.0.0/16"}], [])

    def test_existing_docker_subnet_collision_is_rejected(self):
        with self.assertRaisesRegex(LabError, "overlaps"):
            check_subnets([], [{"IPAM": {"Config": [{"Subnet": "198.51.100.0/24"}]}}])

    def test_single_host_address_in_local_table_is_also_a_collision(self):
        with self.assertRaisesRegex(LabError, "overlaps"):
            check_subnets([{"dst": "192.0.2.3", "table": "local", "type": "local"}], [])

    def test_default_route_and_unrelated_ranges_do_not_collide(self):
        check_subnets([{"dst": "default"}, {"dst": "10.0.0.0/16"}],
                      [{"IPAM": {"Config": [{"Subnet": "fd00::/64"}]}}])

    def test_remote_docker_environment_does_not_redirect_the_lab(self):
        with patch.dict("os.environ", {"DOCKER_HOST": "tcp://remote.invalid:2375",
                                      "DOCKER_CONTEXT": "production",
                                      "DOCKER_TLS_VERIFY": "1",
                                      "DOCKER_CERT_PATH": "/not-used"}):
            docker = Docker()
        self.assertEqual(docker.argv(["info"]), ["docker", "--host", SOCKET, "info"])
        self.assertNotIn("DOCKER_HOST", docker.env)
        self.assertNotIn("DOCKER_CONTEXT", docker.env)
        self.assertNotIn("DOCKER_CERT_PATH", docker.env)


class TracerouteEvidenceTests(unittest.TestCase):
    header = f"traceroute to {SERVER} ({SERVER}), 4 hops max, 46 byte packets\n"

    def test_two_numbered_replies_in_the_expected_order(self):
        output = self.header + f" 1  {ROUTER_LEFT}  0.006 ms\n 2  {SERVER}  0.002 ms\n"
        self.assertTrue(traceroute_reaches_expected_hops(output))

    def test_heading_timeouts_errors_and_nonmatching_addresses_are_not_arrival(self):
        fixtures = {
            "destination times out": f" 1  {ROUTER_LEFT}  0.005 ms\n 2  *\n 3  *\n",
            "router unreachable": f" 1  {ROUTER_LEFT}  0.005 ms !H\n",
            "destination filtered": f" 1  {ROUTER_LEFT}  0.005 ms\n 2  {SERVER}  0.01 ms !X\n",
            "heading and diagnostic only": f"gateway candidate: {ROUTER_LEFT}\n",
            "reversed hops": f" 1  {SERVER}  0.005 ms\n 2  {ROUTER_LEFT}  0.01 ms\n",
            "router address prefix": f" 1  {ROUTER_LEFT}0  0.005 ms\n 2  {SERVER}  0.01 ms\n",
            "destination address prefix": f" 1  {ROUTER_LEFT}  0.005 ms\n 2  {SERVER}0  0.01 ms\n",
        }
        for case, rows in fixtures.items():
            with self.subTest(case=case):
                self.assertFalse(traceroute_reaches_expected_hops(self.header + rows))


if __name__ == "__main__":
    unittest.main()
