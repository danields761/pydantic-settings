import more_itertools
import yaml
from yaml import Dumper
import itertools
from pydantic_settings.types import Json


class PathRebuilder:
    def __init__(self):
        self._pending_event = None
        self._processor = self._process(self._events_stream())
        self._processor.send(None)

    def add_event(self, event):
        self._pending_event = event
        return self._processor.send(event)

    def _events_stream(self):
        # remember previous event and don't let it emit same value twice mistakenly
        prev_event = yield
        while True:
            prev_event = yield prev_event

    def _process(self, stream):
        for event in stream:
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
            yield from self._delegate_processing(event, stream, ())

    def _delegate_processing(self, event, stream, loc):
        yield loc
        if isinstance(event, yaml.MappingStartEvent):
            yield from self._process_map(stream, loc)
        elif isinstance(event, yaml.SequenceStartEvent):
            yield from self._process_seq(stream, loc)

    def _process_seq(self, stream, loc):
        before_seq_end_stream = itertools.takewhile(
            lambda e: not isinstance(e, yaml.SequenceEndEvent), stream
        )
        for i, event in enumerate(before_seq_end_stream):
            yield from self._delegate_processing(event, stream, loc + (i,))

    def _process_map(self, stream, loc):
        before_map_end_stream = itertools.takewhile(
            lambda e: not isinstance(e, yaml.MappingEndEvent), stream
        )
        for key, val in more_itertools.chunked(before_map_end_stream, 2):
            yield from self._delegate_processing(val, stream, loc + (key.value))


class _Dumper(Dumper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path_rebuilder = PathRebuilder()

    def emit(self, event):
        maybe_path = self.path_rebuilder.add_event(event)
        print(event, maybe_path)
        super().emit(event)


def dump(data: Json):
    pass
