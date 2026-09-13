package policy_test

import (
	"bytes"
	"fmt"
	"os"
	"slices"
	"testing"

	"github.com/google/cel-go/cel"
	"github.com/google/cel-go/common/types"
	admissionv1 "k8s.io/api/admissionregistration/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/yaml"
	"k8s.io/apiserver/pkg/admission"
	"k8s.io/apiserver/pkg/admission/plugin/webhook/predicates/rules"
)

// Exercise the published manifest with Kubernetes' own rule matcher and the
// CEL evaluator. This is an offline admission-contract test, not an API server.
func TestReplicaPolicy(t *testing.T) {
	source, err := os.ReadFile("../replica-policy.yaml")
	if err != nil {
		t.Fatal(err)
	}
	decoder := yaml.NewYAMLOrJSONDecoder(bytes.NewReader(source), 4096)
	var policy admissionv1.ValidatingAdmissionPolicy
	var binding admissionv1.ValidatingAdmissionPolicyBinding
	if err := decoder.Decode(&policy); err != nil {
		t.Fatal(err)
	}
	if err := decoder.Decode(&binding); err != nil {
		t.Fatal(err)
	}
	if policy.Spec.MatchConstraints == nil || binding.Spec.MatchResources == nil {
		t.Fatal("policy and binding require match constraints")
	}
	if binding.Spec.PolicyName != policy.Name {
		t.Fatal("binding does not select the published policy")
	}
	selector, err := metav1.LabelSelectorAsSelector(binding.Spec.MatchResources.NamespaceSelector)
	if err != nil {
		t.Fatal(err)
	}
	env, err := cel.NewEnv(cel.Variable("object", cel.DynType))
	if err != nil {
		t.Fatal(err)
	}
	programs := make([]cel.Program, 0, len(policy.Spec.Validations))
	for _, validation := range policy.Spec.Validations {
		ast, issues := env.Compile(validation.Expression)
		if issues.Err() != nil {
			t.Fatal(issues.Err())
		}
		program, err := env.Program(ast)
		if err != nil {
			t.Fatal(err)
		}
		programs = append(programs, program)
	}
	allows := func(namespace, subresource string, operation admission.Operation, replicas *int64) bool {
		if !selector.Matches(labels.Set{"kubernetes.io/metadata.name": namespace}) {
			return true
		}
		kind := schema.GroupVersionKind{Group: "apps", Version: "v1", Kind: "Deployment"}
		if subresource == "scale" {
			kind = schema.GroupVersionKind{Group: "autoscaling", Version: "v1", Kind: "Scale"}
		}
		attributes := admission.NewAttributesRecord(
			nil, nil, kind, namespace, "reviewed-web",
			schema.GroupVersionResource{Group: "apps", Version: "v1", Resource: "deployments"},
			subresource, operation, nil, false, nil,
		)
		matched := false
		for _, rule := range policy.Spec.MatchConstraints.ResourceRules {
			matcher := rules.Matcher{Rule: rule.RuleWithOperations, Attr: attributes}
			matched = matched || matcher.Matches()
		}
		if !matched || !slices.Contains(binding.Spec.ValidationActions, admissionv1.Deny) {
			return true
		}
		spec := map[string]any{}
		if replicas != nil {
			spec["replicas"] = *replicas
		}
		for _, program := range programs {
			value, _, err := program.Eval(map[string]any{"object": map[string]any{"spec": spec}})
			if err != nil {
				return policy.Spec.FailurePolicy != nil && *policy.Spec.FailurePolicy == admissionv1.Ignore
			}
			if value != types.True {
				return false
			}
		}
		return true
	}
	for _, namespace := range []string{"production", "development"} {
		for _, request := range []struct {
			name        string
			subresource string
			operation   admission.Operation
		}{
			{"create-deployment", "", admission.Create},
			{"update-deployment", "", admission.Update},
			{"update-scale", "scale", admission.Update},
		} {
			for _, replicas := range []int64{0, 1, 5, 6} {
				t.Run(fmt.Sprintf("%s/%s/%d", namespace, request.name, replicas), func(t *testing.T) {
					want := namespace != "production" || replicas >= 1 && replicas <= 5
					if got := allows(namespace, request.subresource, request.operation, &replicas); got != want {
						t.Fatalf("allowed=%v, want %v", got, want)
					}
				})
			}
		}
	}
	t.Run("status-updates-are-outside-the-policy", func(t *testing.T) {
		replicas := int64(6)
		if !allows("production", "status", admission.Update, &replicas) {
			t.Fatal("replica policy must not intercept the status subresource")
		}
	})
}
