# events-sourcing-archi-python

(Yet) untested, unproved, opinionated events sourcing architecture skeleton in Python.
Must be tested and proved.

Inspired by [this article](https://www.martinfowler.com/eaaDev/EventSourcing.html).

This required a lot of reading and thinking, and I'm not sure I got it right. I'm not even sure I got it wrong. I'm not sure I got it at all.

Work with python 3.12+ as it uses the new [Generic Types notation](https://docs.python.org/3/library/typing.html#typing.Generic).

## Types

### Aggregates

The basic type is the `Aggregate`, in the meaning of the 
[DDD](https://en.wikipedia.org/wiki/Domain-driven_design) pattern. It is a class that holds the state of a domain object, and that can be modified by applying events to it.

`Aggregates` is mainly a collection of `Events`. They can be replayed to rebuild the state of the `Aggregate`.

### Events

`Events` are immutable objects that represent a change in the state of an `Aggregate`. They are the only way to modify the state of an `Aggregate`.

They are attached to a single `Aggregate`. That's why they are bounded to generic `Aggregate`. They are responsible for the mutation of the `Aggregate`.

They are stored in an `EventStore`.

### EventStore

`EventStore` is a collection of `Events`. It is responsible for the persistence of `Events` bounded to an `Aggregate`. So, indirectly, `EventStore` is bounded to an `Aggregate`.

### Views

`Views` are the read side of the architecture. They are responsible for the persistence of the state of an `Aggregate`. They are bounded to an `Aggregate`. They are eventually consistent with `EventsStore`. They can be updated (or not) within the same `EventStores` transaction.


### Unit of Work

`UnitOfWork` ensures that the `EventStore` (and maybe the `Views`) are updated in a consistant way. They ensure the consistance of one or more `Aggregates`.
