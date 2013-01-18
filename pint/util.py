import time
import math

class TimeLength(object):
    _time_unit_map = [
        ('second', 1),
        ('minute', 60),
        ('hour',   60),
        ('day',    24),
        ('month',  30.5),
        ('year',   12)
    ]

    def __init__(self, timestamp):
        self.timestamp = time.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')

    def from_now(self):
        reference_point = time.mktime(self.timestamp)
        current_point   = time.mktime(time.gmtime())

        return math.floor(current_point - reference_point)

    def from_now_readable(self):
        time_difference = self.from_now()
        unit_name       = None

        for name, divider in self._time_unit_map:
            diff = math.floor(time_difference / divider)

            if diff < 1:
                break

            time_difference = diff
            unit_name       = name

        return '{} {}{}'.format(time_difference, unit_name, '' if time_difference == 1 else 's')

    def __str__(self):
        return self.from_now_readable()