package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	corev1 "k8s.io/api/core/v1"
	podresources "k8s.io/component-helpers/resource"
)

func main() {
	var pods corev1.PodList
	decoder := json.NewDecoder(io.LimitReader(os.Stdin, 16<<20))
	if err := decoder.Decode(&pods); err != nil {
		fmt.Fprintln(os.Stderr, "invalid PodList:", err)
		os.Exit(1)
	}
	var cpuMilli, memoryBytes int64
	var activePods int
	for i := range pods.Items {
		pod := &pods.Items[i]
		if pod.Status.Phase == corev1.PodSucceeded || pod.Status.Phase == corev1.PodFailed {
			continue
		}
		requests := podresources.PodRequests(pod, podresources.PodResourcesOptions{})
		cpuMilli += requests.Cpu().MilliValue()
		memoryBytes += requests.Memory().Value()
		activePods++
	}
	result := struct {
		ActivePods   int   `json:"activePods"`
		CPURequestM  int64 `json:"cpuRequestMillicores"`
		MemoryBytes  int64 `json:"memoryRequestBytes"`
	}{activePods, cpuMilli, memoryBytes}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
