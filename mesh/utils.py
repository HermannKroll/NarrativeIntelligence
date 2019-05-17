import datetime

from lxml import etree


def get_datetime(element, name, is_required=False):
    try:
        return datetime.datetime(
            year=int(element.xpath(f"{name}/Year")[0].text),
            month=int(element.xpath(f"{name}/Month")[0].text),
            day=int(element.xpath(f"{name}/Day")[0].text),
        )
    except IndexError as e:
        if is_required:
            raise IndexError(e)
        else:
            return None


def get_text(element, name, is_required=False):
    try:
        return element.xpath(name)[0].text.strip()
    except IndexError as e:
        if is_required:
            raise ValueError(
                "Error selecting {} from {}. Element is required. Base exception: {}".format(
                    name, etree.tostring(element, pretty_print=True), e))
        else:
            return ""


def get_list(element, name, func, children_required=False):
    return [func(x, children_required) for x in element.xpath(f"{name}/child::*")]


def get_attr(element, name):
    return element.get(name)


# Specific

def get_previous_indexing(element, is_required=False):
    return element.text
    # return get_text(element, "PreviousIndexing", is_required)


def get_tree_number(element, is_required=False):
    return element.text
    # return get_text(element, "TreeNumber", is_required)


def get_related_registry_number(element, is_required=False):
    return element.text
    # return get_text(element, "RelatedRegistryNumber", is_required)


def get_thesaurus_id(element, is_required=False):
    return element.text
    # return get_text(element, "ThesaurusID", is_required)
