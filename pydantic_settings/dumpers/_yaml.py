import itertools

import yaml
from typing import Dict, Tuple, Union, List
from yaml import Dumper

from pydantic_settings.dumpers.common import CommentStr
from pydantic_settings.types import Json


class LocationRebuilder:
    def __init__(self):
        self._pending_event = None
        self._processor = self._process()
        self._processor.send(None)
        self.last_loc = None

    def add_event(self, event):
        self.last_loc = self._processor.send(event)
        return self.last_loc

    def _process(self):
        while True:
            event = yield None
            if isinstance(
                event,
                (
                    yaml.DocumentStartEvent,
                    yaml.DocumentEndEvent,
                    yaml.StreamStartEvent,
                    yaml.StreamEndEvent,
                ),
            ):
                continue
            yield from self._delegate_processing(event, ())

    def _delegate_processing(self, event, loc):
        if isinstance(event, yaml.MappingStartEvent):
            yield from self._process_map(loc)
        elif isinstance(event, yaml.SequenceStartEvent):
            yield from self._process_seq(loc)

    def _process_seq(self, loc):
        for i in itertools.count():
            event = yield loc + (i,)
            if isinstance(event, yaml.SequenceEndEvent):
                return
            yield from self._delegate_processing(event, loc + (i,))

    def _process_map(self, loc):
        while True:
            key = yield None
            if isinstance(key, yaml.MappingEndEvent):
                return
            val = yield loc + (key.value,)
            yield from self._delegate_processing(val, loc + (key.value,))


class _Dumper(Dumper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loc_rebuilder = LocationRebuilder()
        self.comments: Dict[Tuple[Union[str, int], ...], List[CommentStr]] = {}

    def _segregate_comments(self, target, loc):
        if isinstance(target, list):
            new_target = []
            loc_func = lambda k: loc + (len(new_target),)  # noqa: E731
            get_comment_field = lambda k, v: v  # noqa: E731
            add_item = lambda k, v: new_target.append(v)  # noqa: E731
            iter_items = enumerate(target)
        elif isinstance(target, dict):
            new_target = {}
            loc_func = lambda k: loc + (k,)  # noqa: E731
            get_comment_field = lambda k, v: k  # noqa: E731
            add_item = new_target.__setitem__
            iter_items = target.items()
        else:
            raise TypeError(f'unexpected target type {type(target)}')

        prev_comments = []
        new_loc = loc
        for key, item in iter_items:
            comment_field = get_comment_field(key, item)
            if isinstance(comment_field, CommentStr):
                prev_comments.append(comment_field)
            else:
                new_loc = loc_func(key)

                if isinstance(item, (list, dict)):
                    item = self._segregate_comments(item, new_loc)

                add_item(key, item)

                if len(prev_comments) > 0:
                    self.comments[new_loc] = prev_comments
                    prev_comments = []

        if len(prev_comments) > 0:
            self.comments.setdefault(new_loc, []).extend(prev_comments)
        return new_target

    def represent(self, data):
        super().represent(self._segregate_comments(data, ()))

    def expect_node(self, root=False, sequence=False, mapping=False, simple_key=False):
        self.loc_rebuilder.add_event(self.event)
        super().expect_node(root, sequence, mapping, simple_key)

    def expect_block_sequence_item(self, first=False):
        try:
            comments = self.comments[self.loc_rebuilder.last_loc]
            for comment in comments:
                self.write_indent()
                self.stream.write('# ')
                self.stream.write(comment)
                self.write_line_break()
        except KeyError:
            pass

        super().expect_block_sequence_item(first)

    def expect_block_mapping_key(self, first=False):
        if self.loc_rebuilder.last_loc is not None:
            try:
                comments = self.comments[self.loc_rebuilder.last_loc]
                for comment in comments:
                    self.write_indent()
                    self.stream.write('# ')
                    self.stream.write(comment)
                    self.write_line_break()
            except KeyError:
                pass

        super().expect_block_mapping_key(first)

    def _write_block_list_comment(self, comment):
        self.write_line_break()
        self.write_indent()
        self.stream.write('# ')
        self.stream.write(comment)

    def _write_block_map_comment(self, comment):
        self.stream.write('# ')
        self.stream.write(comment)
        self.write_line_break()
        self.write_indent()


def dump(data: Json):
    pass
