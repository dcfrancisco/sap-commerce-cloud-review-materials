# M03 — Type System, items.xml, and Data Modeling

**Release:** 0.1.0 · **Status:** complete for milestone slice · **Competencies:** C-TYPE-001, C-TYPE-002

## Purpose

Modeling is an executable design decision. In SAP Commerce, type definitions, generated model classes, relations, persistence choices, and initialization/update behavior are connected. This chapter teaches how to design a small model change and identify the operational consequences.

## SAP-specific foundations

SAP states that an extension’s `items.xml` defines types and can define, override, or extend attributes. It is located under the extension resources directory and is validated against an XSD [SAP-HELP-ITEMS]. The documented basic structure includes atomic, collection, enum, map, relation, and item type definitions. Definition order matters because the file is parsed in a single pass; an invalid order can fail the extension build [SAP-HELP-ITEMS].

SAP’s data-model documentation describes item types and relations and explains that extension declarations are combined during build and database initialization to generate Java classes and a database schema [SAP-HELP-DATA-MODELS]. A runtime type created only through administration tooling is not equivalent to a source-backed configured type: SAP documents that runtime types are lost on initialization and have no generated Java source [SAP-HELP-RUNTIME-TYPES].

## Design sequence

1. Name the business invariant, not merely the column.
2. Decide whether the concept is an item type, an attribute, an enum, or a relation.
3. Choose ownership and cardinality.
4. Decide optionality, searchability, localization, and collection semantics.
5. Decide persistence and deployment implications.
6. Plan initial data, migration, rollback, and generated code impact.
7. Add service/API behavior and tests only after the model is understood.

Example requirement: “a product can have several compliance documents, each with a locale and effective date.” A relation may preserve document identity and queryability better than a serialized collection. That is an engineering decision; the correct choice depends on access patterns and supported platform conventions.

## Example `items.xml` fragment

```xml
<items xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:noNamespaceSchemaLocation="items.xsd">
  <itemtypes>
    <itemtype code="ComplianceDocument"
              extends="GenericItem"
              autocreate="true"
              generate="true">
      <attributes>
        <attribute qualifier="documentId" type="java.lang.String">
          <modifiers optional="false" unique="true"/>
          <persistence type="property"/>
        </attribute>
        <attribute qualifier="effectiveFrom" type="java.util.Date">
          <persistence type="property"/>
        </attribute>
      </attributes>
    </itemtype>
  </itemtypes>
</items>
```

This illustrates the documented XML shape, not a production-ready model. Before use, verify the type, modifiers, deployment, relation, and migration requirements for the targeted release. Never infer that `unique="true"` alone solves concurrent writes or historical data quality.

## Initialization, update, and runtime types

Source-backed type changes have lifecycle impact. A build can generate model sources, but application code also depends on the running type system and database state. An initialization may recreate the type system and remove types not backed by source definitions; an update may apply a narrower change depending on the platform procedure. Treat initialization as destructive to data unless verified otherwise. This is why a production change needs a migration and restore plan, not only a successful compile.

## Deployment tables and typecodes

SAP documents two persistence choices for a new item type: use a dedicated deployment table, or inherit the table used by an ancestor. Without a deployment declaration, a subtype is persisted in the ancestor's table [RS-SAP-HELP-DB-DESIGN]. This choice affects row density, indexes, query plans, lifecycle coupling, and the cost of later migration. It is not a cosmetic XML preference.

The official learning material further states that direct subtypes of `GenericItem` should specify a deployment table, and that many-to-many relations require deployment information for their link table [RS-SAP-LEARN-DEPLOYMENT]. Before assigning a typecode, inspect the complete project and platform type system; uniqueness must hold across the installation, not just within one file.

### Evolution scenarios

Do not promise that removing or changing an `items.xml` declaration automatically removes the old database structure. SAP's update-scenario documentation describes data-protection cases where old deployment structures can remain as metadata/orphaned structures [RS-SAP-HELP-TYPE-UPDATES]. For each schema change, classify it as additive, constraint-tightening, type conversion, relation migration, deployment move, or removal. Then define:

1. precondition queries and data-quality checks;
2. generated-model and compile impact;
3. update-system behavior supported by the target release;
4. explicit data migration and rollback;
5. database-vendor validation;
6. post-update FlexibleSearch and service tests;
7. production telemetry and recovery threshold.

An independent engineering guide emphasizes the long-lived cost of incorrect deployment-table and hierarchy decisions [RS-INDEPENDENT-CCI-DATA]. That source is used only as design rationale; supported update behavior remains governed by SAP documentation and target-runtime evidence.

## Failure analysis

| Symptom | Investigation |
| --- | --- |
| XSD/build failure | validate XML, order, attributes, and release schema |
| generated getter missing | confirm extension selected and model generation completed |
| type exists locally but not in target | compare update/initialization evidence and release manifest |
| relation query returns duplicates | inspect cardinality, joins, and fixture assumptions |
| runtime type disappears | confirm whether it is source-backed before initialization |

## Guided lab — model a compliance relation

Create a design record for `ComplianceDocument`, the product-document relation, and a localized title. Include cardinality, ownership, deletion behavior, query use cases, migration steps, and tests. **Acceptance:** the design distinguishes configured type from runtime type, calls out version-sensitive choices, and includes one data-quality invariant.

## Independent practice

Choose between a subtype, an attribute, and a relation for “product has a primary sustainability rating plus audit history.” Defend the choice under these constraints: backoffice editing, OCC read exposure, historical reporting, and a future data import.

## Testing competency — prove runtime type and persistence invariants

An `items.xml` fragment can be syntactically valid while its generated model, runtime type metadata, database constraint, relation behavior, or migration is wrong. A POJO unit test is useful for a converter or validator but cannot prove platform persistence. SAP integration tests require a started Commerce environment and can use real items in the JUnit tenant [RS-SAP-TESTING-JUNIT] [RS-SAP-TESTING-EXECUTION].

For the compliance-document example, begin with pure unit tests for code normalization and mapping. Then use a target-version transactional platform test for persistence:

```java
@IntegrationTest
class ComplianceDocumentPersistenceTest
    extends PlatformJUnit5TransactionalTest {
  @Resource ModelService modelService;
  @Resource FlexibleSearchService flexibleSearchService;

  @Test void sameCodeMayExistInDifferentCatalogVersions() {
    // Create isolated Staged and Online versions, persist both, query both.
  }

  @Test void duplicateWithinOneVersionIsRejected() {
    // Persist one identity, attempt a duplicate, assert final row count.
  }
}
```

The class name illustrates current documented JUnit 5 infrastructure; exact inheritance, fixtures, imports, and failure types must be verified for the selected update line [RS-SAP-TESTING-JUNIT5]. Negative tests cover duplicate identity, invalid relation cardinality, missing mandatory values, delete behavior, and failed migration preconditions. Query final persisted state rather than accepting “save did not throw” as proof.

Execution evidence records the test-system baseline, update line, type-system update, fixture identifiers, command, red result before repair, green result after repair, query assertions, and cleanup or transaction isolation. No generated model or JUnit tenant exists in this repository; `DEV-EX-M03-001` assesses the test design but is not executed SAP Commerce persistence evidence.

## References

- [SAP-HELP-ITEMS] `items.xml`.
- [SAP-HELP-DATA-MODELS] Data Models.
- [SAP-HELP-RUNTIME-TYPES] Configured Types vs Runtime Types.
- [RS-SAP-HELP-DB-DESIGN] Database Design.
- [RS-SAP-HELP-TYPE-UPDATES] Update Scenarios.
- [RS-SAP-LEARN-DEPLOYMENT] Analyzing Data Type Deployment.
- [RS-INDEPENDENT-CCI-DATA] Independent data-modeling guide; supplementary, not authoritative.
- [RS-SAP-TESTING-JUNIT] Testing with JUnit.
- [RS-SAP-TESTING-JUNIT5] Testing with JUnit 5.
- [RS-SAP-TESTING-EXECUTION] Writing and Executing Tests.
