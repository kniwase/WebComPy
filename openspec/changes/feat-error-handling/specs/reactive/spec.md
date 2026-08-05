# Delta: reactive

## ADDED Requirements

### Requirement: Consumer notification shall be isolated per consumer

When a producer notifies its consumers, an exception raised by one consumer's mark-dirty/dispatch path SHALL NOT prevent the remaining consumers from being notified. The failing consumer's exception SHALL be routed into the error-handling pipeline (global handler or log). The producer's value commit, the same-value-set equality skip (`old is new or old == new`), and Computed lazy-evaluation contracts SHALL be unchanged. Notification-phase bookkeeping (`_in_notification_phase`) SHALL be correctly restored even when consumers raise.

#### Scenario: Failing consumer does not block siblings
- **WHEN** a signal has three subscribers and the first subscriber's callback raises
- **THEN** the second and third subscribers SHALL still be notified with the new value
- **AND** the error SHALL be reported via the error-handling pipeline

#### Scenario: Producer state consistency
- **WHEN** a consumer raises during notification
- **THEN** the producer's value SHALL remain the newly set value
- **AND** subsequent reads of sibling Computed consumers SHALL recompute correctly (no stuck-dirty state)

#### Scenario: Notification phase restored
- **WHEN** a consumer raises during notification
- **THEN** `_in_notification_phase` SHALL be `False` after the notification completes
