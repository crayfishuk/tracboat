# -*- coding: utf-8 -*-

import six
from pprint import pprint

class LabelAbstract():
    TYPE = None
    COLOR = None
    ATTRIBUTE_NAME = None
    MAPPING = {}

    def __init__(self, title):
        self.title = self.convert_value(title)

    @classmethod
    def convert_value(cls, title):
        if title in cls.MAPPING:
            return cls.MAPPING[title]
        else:
            return title

    @classmethod
    def from_ticket(cls, ticket):
        """
        yield possible names from trac ticket
        """
        attribute_name = cls.ATTRIBUTE_NAME
        try:
            values = ticket['attributes'][attribute_name].split(',')
        except KeyError:
            values = []
            pass

        for value in values:
            yield value

        # get versions from changelog
        for change in ticket['changelog']:
            if change['field'] == attribute_name:
                yield change['oldvalue']
                yield change['newvalue']

class LabelPriority(LabelAbstract):
    TYPE = 'priority'
    COLOR = '#D9534F'
    ATTRIBUTE_NAME = 'priority'
    MAPPING = {
        'Fatal': 'P1',
        'Critical': 'P2',
        'Major': 'P3',
        'Medium': 'P4',
        'Minor': 'P5',
        'Cosmetic': 'P6',
    }

class LabelResolution(LabelAbstract):
    TYPE = 'resolution'
    COLOR = '#7F8C8D'
    ATTRIBUTE_NAME = 'resolution'
    MAPPING = {
        'fixed': 'closed:fixed',
        'invalid': 'closed:invalid',
        'wontfix': 'closed:wontfix',
        'duplicate': 'closed:duplicate',
        'worksforme': 'closed:worksforme',
    }

class LabelVersion(LabelAbstract):
    TYPE = 'version'
    COLOR = '#5CB85C'
    ATTRIBUTE_NAME = 'version'

class LabelComponent(LabelAbstract):
    TYPE = 'component'
    COLOR = '#428BCA'
    ATTRIBUTE_NAME = 'component'

class LabelType(LabelAbstract):
    TYPE = 'type'
    COLOR = '#D10069'
    ATTRIBUTE_NAME = 'type'

class LabelStatus(LabelAbstract):
    TYPE = 'status'
    COLOR = '#0033CC'
    ATTRIBUTE_NAME = 'status'
    MAPPING = {
        'new': 'opened',
        'assigned': 'opened',
        'accepted': 'opened',
        'active': 'opened',
        'reopened': 'opened',
        'defer': 'closed',
        'fixed': 'closed',
        'review': 'closed',
        'tested': 'closed',
        'closed': 'closed',
    }

class LabelSet():
    def __init__(self):
        self.labels = {}
        self.label_by_type = {}

    def __len__(self):
        return len(self.labels)

    def add(self, label):
        self.labels.update({label.title: label})
        self.label_by_type[label.TYPE] = label

    def values(self):
        return self.labels.values()

    def add_many(self, labels):
        for label in labels:
            self.add(label)

    def get_status_label(self):
        return self.label_by_type[LabelStatus.TYPE]

    def get_label_titles(self):
        return [x.title for x in self.values()]

# class handling labels management
# when in trac we have 
# then in gitlab we have just labels
class LabelManager():
    def __init__(self, gitlab, logger):
        self.gitlab = gitlab
        self.logger = logger
        self.issues = {}
        self.classes = [
            LabelPriority,
            LabelResolution,
#            LabelVersion,
            LabelComponent,
            LabelType,
#            LabelStatus,
        ]

    def collect_labels(self, tickets):
        """
        Walk over tickets list,
        caches result in ticket object "labels" key.
        """

        self.logger.info('Labels: process %d tickets', len(tickets))
        # labels of all issues
        labels = LabelSet()
        for ticket_id, ticket in six.iteritems(tickets):
            if not 'labels' in ticket:
                ticket['labels'] = self.ticket_labels(ticket)
            labels.add_many(ticket['labels'].values())

        return labels

    def create_labels(self, tickets):
        """
        Create Labels in gitlab.
        Caches result in ticket object "labels" key.
        """

        labels = self.collect_labels(tickets)
        self.logger.info('Labels: Create %d labels', len(labels))

        for label in labels.values():
            self.gitlab.create_label(label)

    def ticket_labels(self, ticket):
        """
        Get labels related to Trac ticket
        """

        labels = LabelSet()

        for cls in self.classes:
            gen = self.factory(cls, ticket)
            labels.add_many(gen)

        return labels

    def factory(self, cls, ticket):
        for title in cls.from_ticket(ticket):
            if title != '':
                yield cls(title)
