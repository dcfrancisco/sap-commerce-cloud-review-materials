# M04 — ModelService, Persistence, Transactions, and ServiceLayer

**Release:** 0.1.0 · **Status:** complete for milestone slice · **Competencies:** C-SERVICE-001, C-SERVICE-002

## Purpose

This chapter turns a data model into a safe use case. It focuses on DAO/service/facade separation, generated models, transaction scope, FlexibleSearch reasoning, and failure evidence. SAP-specific mechanics are identified separately from general Spring design guidance.

## SAP facts and engineering interpretation

SAP documents the ServiceLayer as the API layer of choice and provides procedures for displaying users/products, adding models, and implementing services [SAP-HELP-ITEMS] [SAP-HELP-SERVICELAYER]. The platform documentation also describes transactions through its transaction API and Spring integration. SAP’s `HybrisTransactionManager` delegates to the platform transaction framework, and Spring transaction declarations can be used [SAP-HELP-TRANSACTIONS].

The engineering interpretation is: put business invariants in an application service, keep retrieval-specific query logic in a DAO, keep external representations in converters/facades, and make transaction scope explicit. These are design principles, not promises that every SAP extension must have the same class names.

## Request path

```text
OCC/controller -> facade/use case -> service invariant
                              -> DAO/FlexibleSearch -> models
                              -> transaction boundary -> persistence
```

The service should answer “is this operation allowed?” The DAO should answer “how do I retrieve the data?” The facade should answer “what shape does this use case expose?” Mixing these responsibilities makes tests broad and failure diagnosis vague.

## Transaction reasoning

A transaction should contain the smallest set of state changes that must succeed or fail together. Do not hold a database transaction across an unbounded remote HTTP call. If an order write and an external reservation must coordinate, design a durable state transition, retry/idempotency key, and reconciliation path rather than assuming a distributed transaction.

SAP documents that transactions are thread-associated and that nested transaction calls participate in the existing transaction rather than creating an independent database transaction [SAP-HELP-TRANSACTIONS]. That means a helper method’s `begin()` is not proof of isolation. Test the actual boundary and rollback behavior.

```java
@Transactional
public OrderResult submit(SubmitOrderCommand command) {
    CartModel cart = cartDao.load(command.cartId());
    validator.validate(cart, command);
    OrderModel order = orderFactory.create(cart);
    modelService.save(order);
    return orderConverter.convert(order);
}
```

The annotation is illustrative. Verify the supported transaction annotation, proxying rules, and bean configuration for the target Commerce release. A self-invocation may bypass a Spring proxy; a test must prove whether the intended transaction is active.

## FlexibleSearch discipline

Write the business question first, then the query. Define selected fields, joins, filters, ordering, and expected cardinality. Avoid using a broad query to compensate for an unclear model. Test empty, duplicate, authorization-filtered, and large-result cases. A query that works against a tiny fixture can still fail operationally through poor selectivity or excessive result materialization.

## Guided lab — transaction failure

Use the simulation scenario `LAB-M04-ROLLBACK`. The scenario attempts a stock reservation and an order state change, then injects a failure between them. Record the invariant, expected rollback, correlation ID, and compensating action. **Acceptance:** the learner does not claim the simulator demonstrates SAP’s transaction engine; the answer distinguishes local atomicity from external reconciliation.

## Independent practice

Design a service method that imports 1,000 products, rejects invalid records, and remains restartable. State transaction batch size, error storage, idempotency key, retry behavior, and how partial success is reported.

## Troubleshooting checklist

- Is the service called through the managed bean/proxy?
- Is the transaction boundary wider than the invariant?
- Does a DAO return models or an API DTO?
- Is a remote call inside the transaction?
- Can the operation be retried safely?
- Does rollback evidence include the database state and emitted events?

## References

- [SAP-HELP-SERVICELAYER] Working with the ServiceLayer.
- [SAP-HELP-TRANSACTIONS] Transactions.
- [SAP-HELP-ITEMS] `items.xml` and ServiceLayer context.
