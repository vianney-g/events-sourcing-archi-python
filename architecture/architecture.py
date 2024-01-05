import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import field
from datetime import datetime
from typing import ClassVar, Protocol, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, Json


class Event[A: "Aggregate"](ABC, BaseModel):
    """
    Event from a Events Driven perspective.
    Events are immutable and are used to mutate the Aggregate. They are bounded to a type of Aggregate.

    Event are uniquely identified by their `event_id`. This prevents a same event to be saved twice.

    Implements you own event by subclassing this class and implementing `apply` method.
    """

    model_config = ConfigDict(frozen=True)

    # You may implement another way to generate unique ids.
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    aggregate_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    by: str = ""

    def mutate(self, aggregate: A, /) -> None:
        aggregate.updated_at = self.timestamp
        self.apply(aggregate)

    @abstractmethod
    def apply(self, aggregate: A, /) -> None:
        """Apply the event to the Aggregate.
        This method should be idempotent.
        """
        raise NotImplementedError

    def as_json(self) -> dict:
        return json.loads(
            self.model_dump_json(
                exclude={"event_id", "aggregate_id", "timestamp", "by"}
            )
        )


class EventsRegistry[A: "Aggregate"](dict[str, type[Event[A]]]):
    """
    Registry for Events. It is bounded to a type of Aggregate.
    It can be used as a decorator to register an Event.

    Example:

    ```
    my_aggregate_events: EventsRegistry[MyAggregate] = EventsRegistry()

    @my_aggregate_events.register
    class MyEvent(Event[MyAggregate]):
        ...

    ```
    """

    def register[E: Event](self, event_type: type[E]) -> type[E]:
        self[event_type.__name__] = event_type
        return event_type


class Aggregate(ABC, BaseModel):
    """
    Aggregate from a Events Driven perspective
    """

    id: str = ""
    created_at: datetime = datetime.min
    updated_at: datetime = datetime.min
    # This list contains all events that have been applied to the Aggregate
    # during its lifetime.
    events: list[Event[Self]] = field(default_factory=list)
    events_registry: ClassVar[EventsRegistry]

    @classmethod
    def empty(cls) -> Self:
        return cls()

    def __bool__(self) -> bool:
        return self.created_at is not datetime.min

    @classmethod
    def replay(cls, events: Iterable[Event[Self]]) -> Self:
        """Rebuild an Aggregate from a list of events.
        Event are applied in order, but not saved in `self.events`."""
        obj = cls.empty()
        for event in events:
            event.mutate(obj)
        return obj

    def apply_event(self, event: Event[Self]) -> None:
        """Apply an event to the Aggregate and save it in `self.events`."""
        event.mutate(self)
        self.events.append(event)


class WritableView[A: Aggregate](Protocol):
    """
    View for an Aggregates. It is mutable. Should be eventually consistent with the Events Store.
    """

    def update(self, obj: A, /) -> None:
        ...

    def insert(self, obj: A, /) -> None:
        ...


class ReadView[A: Aggregate](Protocol):
    """
    Following the CQRS pattern, a Read View is a read only view of the Aggregates.
    It is eventually consistent with the Events Store, according to the way is it updated.

    Note that they are not the source of truth for the Aggregates (see EventsStore).
    They may implements caching strategies to improve performance.

    """

    def get(self, id: str) -> A:
        ...


class EventsStore[A: Aggregate](Protocol):
    """
    Suggestion for a Event Store pattern Python interface.
    Events Stores are append only. They are not mutable.
    They are bounded to a type of Event.
    They are the source of truth for the Aggregates.
    """

    def update(self, aggregate: A, /) -> None:
        ...

    def for_aggregate(self, aggregate_id: str, /) -> Iterable[Event[A]]:
        ...

    def get_aggregate(self, aggregate_id: str, /) -> A:
        """Rebuild an Aggregate from the events store."""
        # most of the time the code will be:
        # return Aggeregate.replay(self.for_aggregate(aggregate_id))
        ...


class UnitOfWork(Protocol):
    """
    Suggestion for a Unit Of Work pattern (as described by Martin Fowler) Python interface.

    Implemented as an context manager. Up to you to make `__exit__` commit (in case of no error)
    or rollback by default.
     - Commit by default may be a little less verbose.
     - Rollback by default means commit is explicit. This is more safe as it leads to a safe state
       event if the context manager is exited early. There is a single point of commit.
    """

    def __enter__(self) -> None:
        ...

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class Command[U: UnitOfWork](Protocol):
    """Commands should be self describing, immutable and executable.
    They are bounded to a unit of work.
    """

    def __call__(self, uow: U) -> Result[Json, Json]:
        ...
