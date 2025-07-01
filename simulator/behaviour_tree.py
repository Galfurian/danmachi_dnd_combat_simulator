# behaviour_tree.py
from enum import Enum, auto
from typing import Any, Callable, Optional


class BTStatus(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()


class Node:
    def tick(self, ctx: Any) -> BTStatus:
        raise NotImplementedError()


class Action(Node):
    def __init__(self, fn: Callable[[Any], BTStatus], name: Optional[str] = None):
        self.fn = fn
        self.name = name or fn.__name__

    def tick(self, ctx: Any) -> BTStatus:
        return self.fn(ctx)


class Condition(Node):
    def __init__(self, test: Callable[[Any], bool], name: Optional[str] = None):
        self.test = test
        self.name = name or test.__name__

    def tick(self, ctx: Any) -> BTStatus:
        return BTStatus.SUCCESS if self.test(ctx) else BTStatus.FAILURE


class Sequence(Node):
    def __init__(self, *children: Node):
        self.children: list[Node] = list(children)

    def tick(self, ctx: Any) -> BTStatus:
        for c in self.children:
            s = c.tick(ctx)
            if s != BTStatus.SUCCESS:
                return s
        return BTStatus.SUCCESS


class Selector(Node):
    def __init__(self, *children: Node):
        self.children: list[Node] = list(children)

    def tick(self, ctx: Any) -> BTStatus:
        for c in self.children:
            s = c.tick(ctx)
            if s != BTStatus.FAILURE:
                return s
        return BTStatus.FAILURE
