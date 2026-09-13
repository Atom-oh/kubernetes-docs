package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func requestBody(object string) []byte {
	return []byte(`{"apiVersion":"admission.k8s.io/v1","kind":"AdmissionReview","request":{"uid":"audit-uid","operation":"CREATE","resource":{"group":"","version":"v1","resource":"pods"},"object":` + object + `}}`)
}

func invoke(method, contentType string, body []byte) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, "/mutate", bytes.NewReader(body))
	r.Header.Set("Content-Type", contentType)
	w := httptest.NewRecorder()
	mutate(w, r)
	return w
}

func TestAdmissionContract(t *testing.T) {
	fixtures := []map[string]any{}
	for _, tc := range []struct {
		name, object, path string
	}{
		{"missing-labels", `{"apiVersion":"v1","kind":"Pod","metadata":{"name":"p"}}`, "/metadata/labels"},
		{"null-labels", `{"apiVersion":"v1","kind":"Pod","metadata":{"labels":null}}`, "/metadata/labels"},
		{"existing-labels", `{"apiVersion":"v1","kind":"Pod","metadata":{"labels":{"team":"data"}}}`, "/metadata/labels/example.com~1injected"},
		{"already-labeled", `{"apiVersion":"v1","kind":"Pod","metadata":{"labels":{"example.com/injected":"true","team":"data"}}}`, ""},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := invoke("POST", "application/json; charset=utf-8", requestBody(tc.object))
			if w.Code != http.StatusOK {
				t.Fatalf("status=%d body=%s", w.Code, w.Body)
			}
			var got review
			if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
				t.Fatal(err)
			}
			if got.APIVersion != "admission.k8s.io/v1" || got.Kind != "AdmissionReview" ||
				got.Request != nil || got.Response == nil || got.Response.UID != "audit-uid" || !got.Response.Allowed {
				t.Fatalf("bad response: %+v", got)
			}
			if tc.path == "" {
				if len(got.Response.Patch) != 0 || got.Response.PatchType != "" {
					t.Fatal("reinvocation should not patch")
				}
			} else {
				var ops []patchOperation
				if err := json.Unmarshal(got.Response.Patch, &ops); err != nil {
					t.Fatal(err)
				}
				if got.Response.PatchType != "JSONPatch" || len(ops) != 1 || ops[0].Path != tc.path {
					t.Fatalf("invalid patch: %+v", ops)
				}
			}
			fixtures = append(fixtures, map[string]any{"case": tc.name, "object": json.RawMessage(tc.object), "response": got})
		})
	}
	data, err := json.MarshalIndent(fixtures, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if destination := os.Getenv("ADMISSION_PATCH_FIXTURES"); destination != "" {
		if err := os.WriteFile(destination, data, 0600); err != nil {
			t.Fatal(err)
		}
	}
}

func TestInvalidRequests(t *testing.T) {
	validPod := `{"apiVersion":"v1","kind":"Pod","metadata":{"name":"p"}}`
	for _, tc := range []struct {
		name, method, contentType string
		body                      []byte
		want                      int
	}{
		{"method", "GET", "application/json", requestBody(validPod), 405},
		{"content-type", "POST", "text/plain", requestBody(validPod), 415},
		{"malformed", "POST", "application/json", []byte("{"), 400},
		{"null-request", "POST", "application/json", []byte(`{"apiVersion":"admission.k8s.io/v1","kind":"AdmissionReview","request":null}`), 400},
		{"missing-uid", "POST", "application/json", bytes.ReplaceAll(requestBody(validPod), []byte("audit-uid"), []byte("")), 400},
		{"null-object", "POST", "application/json", requestBody("null"), 400},
		{"wrong-version", "POST", "application/json", bytes.ReplaceAll(requestBody(validPod), []byte("admission.k8s.io/v1"), []byte("admission.k8s.io/v1beta1")), 400},
		{"trailing-json", "POST", "application/json", append(requestBody(validPod), []byte("{}")...), 400},
		{"oversized", "POST", "application/json", requestBody(`{"apiVersion":"v1","kind":"Pod","metadata":{"name":"` + strings.Repeat("a", 1<<20) + `"}}`), 400},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := invoke(tc.method, tc.contentType, tc.body); got.Code != tc.want {
				t.Fatalf("status=%d want=%d", got.Code, tc.want)
			}
		})
	}
}

func TestNonTargetRequestIsUnchanged(t *testing.T) {
	body := bytes.ReplaceAll(requestBody(`{"apiVersion":"v1","kind":"Pod","metadata":{}}`),
		[]byte(`"operation":"CREATE"`), []byte(`"operation":"DELETE"`))
	w := invoke("POST", "application/json", body)
	var got review
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if w.Code != 200 || got.Response == nil || !got.Response.Allowed || len(got.Response.Patch) != 0 {
		t.Fatalf("non-target changed: %s", w.Body)
	}
}
