# M02 — Development Environment, Builds, and Configuration

**Release:** 0.1.0 · **Status:** complete for milestone slice · **Competencies:** C-EXT-001, C-EXT-002

## Purpose

This chapter teaches how a Commerce extension becomes part of a build and how to investigate configuration failures without treating a local simulation as the platform. The SAP-specific claims are scoped to the cited 2205/2211 documentation; command names and project conventions must be checked against the release actually supplied to a team.

## Outcomes and prerequisites

You can explain the role of an extension, identify build inputs, reason about dependencies, distinguish source configuration from runtime state, and produce a reproducible failure report. Prerequisites: Java/Spring basics, XML, Git, and the M01 boundary model.

## SAP facts

SAP describes an extension as an encapsulated unit that may provide business logic, types, web applications, or Backoffice configuration. Extensions are independent by default and can declare dependencies [SAP-HELP-EXTENSION]. A blank extension structure includes resources, source, tests, web code, and library locations; the exact set of components depends on the extension template [SAP-HELP-EXTENSION-COMPONENTS] [SAP-HELP-ABOUT-COMMERCE]. SAP publishes templates such as `yempty`, `yacceleratorcore`, `ycommercewebservices`, `yocc`, and test templates [SAP-HELP-EXTENSION-TEMPLATES].

Do not confuse the following layers:

| Layer | Question | Evidence |
| --- | --- | --- |
| Repository | Is the extension source present and versioned? | Git tree and commit |
| Manifest/build | Is it selected and are dependencies resolvable? | manifest, extension list, build logs |
| Application context | Are Spring beans and properties loaded? | startup logs, context test |
| Type system/database | Is the model updated safely? | update/initialization evidence |
| Cloud environment | Did the target environment receive the build? | Cloud Portal build/deployment record |

## Extension anatomy

```text
myextension/
  resources/
    myextension-items.xml
    localization/
  src/
  testsrc/
  web/
  lib/
  extensioninfo.xml
```

The diagram is a teaching abstraction based on the documented extension structure. A team must validate the actual template and release. Keep domain logic in a core extension, web/API concerns in their appropriate web extension, and fixtures/tests in test locations. This arrangement reduces accidental dependency cycles and makes ownership visible.

## Build reproducibility

A reproducible build answers: which Commerce release, which extension pack, which custom extensions, which Java/runtime assumptions, and which source revision? SAP’s public-cloud docs describe versioned artifacts and extension packs in the manifest/build process [SAP-HELP-EXTENSION-PACKS]. Capture those inputs as build metadata. Never diagnose a deployment from a screenshot that omits the commit and artifact version.

SAP's public sample repository provides a concrete 2211 repository shape with `core-customize/manifest.json`, custom extensions, configuration, `localextensions.xml`, and a separate JavaScript storefront manifest. The repository explicitly warns that deprecated `yacceleratorstorefront` artifacts are included for showcase rather than new development [RS-SAP-GITHUB-CLOUD-SAMPLE]. Treat the sample as versioned executable guidance, not a substitute for the compatibility documentation or a license entitlement.

### JDK 21 framework line

The 2211-jdk21.1 release notes describe a move to JDK 21 and Spring 6, library upgrades, removed deprecated extensions, and OAuth implementation changes [RS-SAP-HELP-JDK21]. A build report must therefore identify the full update line, not merely “2211.” Code that compiles on a JDK 17 update can fail because of `javax` to `jakarta` package changes, removed APIs, Spring proxy/configuration differences, or changed third-party dependencies. The academy treats every update-line change as a compatibility event requiring compile, context, contract, security, and representative workload tests.

### Configuration precedence

Treat configuration as inputs with explicit scope:

1. immutable source defaults;
2. environment-specific non-secret configuration;
3. secret references supplied by the environment;
4. runtime toggles with an owner and rollback path.

This is general engineering guidance. It is not a claim that every SAP property can be supplied through every mechanism. Verify supported configuration channels in the current Cloud Portal and project documentation [SAP-HELP-CLOUD-PORTAL].

## Worked diagnostic

**Symptom:** a custom service compiles locally but the deployed environment fails during startup.

1. Compare the commit, Commerce artifact, extension list, Java version, and build manifest.
2. Determine whether the failure is compilation, class loading, Spring context, type update, or external configuration.
3. Search the first causal exception, not the last cascading error.
4. Confirm the dependency is declared at the correct extension/build level.
5. Reproduce in the smallest supported environment and attach the evidence to the change.

Common mistakes include fixing a missing extension by adding unrelated dependencies, committing secrets into properties, changing a type definition without a migration plan, and declaring a web dependency from core code. Each mistake turns a local symptom into a release risk.

## Guided lab — extension failure report

**Objective:** localize a simulated extension build failure.

**Initial state:** use the lab fixture `LAB-M02-BUILD-DIAGNOSIS` and inspect `buildInputs`, `dependencyGraph`, and `failureStage`.

**Tasks:** identify the missing dependency, name the earliest failing stage, propose one minimal change, and state one regression test. **Acceptance:** the answer distinguishes repository, manifest, context, and runtime-state evidence; it does not claim the simulator is SAP Commerce.

**Reference solution:** repair the declared dependency in the build input, rerun the dependency-resolution check, then execute a context-load test. Do not bypass the failure by adding a global library.

## Independent practice

Design a release checklist for a custom `yocc` extension. Include source revision, extension selection, dependency graph, API contract tests, secrets, environment configuration, rollback, and evidence retention. The learner must defend why each check belongs before deployment rather than after startup failure.

## Assessment focus

The M02 items test extension ownership, dependency diagnosis, configuration scope, and build evidence. Correct answers require reasoning, not recall of a directory tree.

## Testing competency — extension wiring is executable architecture

Compilation does not prove that extensions are selected, dependency declarations are complete, properties resolve correctly, or Spring creates the production bean graph. SAP distinguishes unit tests that do not require a running Commerce environment from integration tests that require SAP Commerce to be started [RS-SAP-TESTING-JUNIT]. Current JUnit 5 guidance is update-line-sensitive and documents platform base tests and runner configuration [RS-SAP-TESTING-JUNIT5].

Use a fast unit test to prove isolated facade behavior:

```java
@ExtendWith(MockitoExtension.class)
class DefaultAcademyFacadeTest {
  @Mock AcademyCoreService coreService;
  @InjectMocks DefaultAcademyFacade facade;

  @Test void delegatesNormalizedCode() {
    facade.findProduct(" acme-1 ");
    verify(coreService).findProduct("ACME-1");
  }
}
```

That test cannot detect a missing `<requires-extension>` declaration. A target-version platform integration test must load the real context and resolve the bean. For update lines where it is supported, a project may use an appropriate JUnit 5 platform/service-layer base such as `ServicelayerJUnit5BaseTest`; verify the exact base and runner against the selected release.

```java
@IntegrationTest
class AcademyContextIntegrationTest extends ServicelayerJUnit5BaseTest {
  @Resource(name = "academyFacade") AcademyFacade academyFacade;

  @Test void productionBeanGraphLoads() {
    assertNotNull(academyFacade);
  }
}
```

Negative-path practice begins with the dependency deliberately absent. Record the first context failure, repair only the declared dependency, rerun the targeted test, and retain the XML report. Required execution evidence includes source revision, Commerce update line, JDK, `tests.runner.legacy` value where applicable, command or pipeline target, failing test identifier, passing rerun, duration, and report location. This repository has no SAP Commerce runtime, so `DEV-EX-M02-001` grades the diagnosis and evidence design but does not claim that the platform integration test ran.

## References

- [SAP-HELP-EXTENSION] Extension Concept.
- [SAP-HELP-EXTENSION-COMPONENTS] Extension Components.
- [SAP-HELP-EXTENSION-TEMPLATES] Available Extension Templates.
- [SAP-HELP-EXTENSION-PACKS] Extension Packs.
- [SAP-HELP-CLOUD-PORTAL] Cloud Portal.
- [RS-SAP-GITHUB-CLOUD-SAMPLE] SAP Commerce Cloud Sample Repository.
- [RS-SAP-HELP-JDK21] Update Release 2211-jdk21.1.
- [RS-SAP-TESTING-JUNIT] Testing with JUnit.
- [RS-SAP-TESTING-JUNIT5] Testing with JUnit 5.
- [RS-SAP-TESTING-EXECUTION] Writing and Executing Tests.
