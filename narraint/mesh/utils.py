import datetime

from lxml import etree


def get_datetime(element, name, is_required=False):
    """
    Create datetime from node. Node has Year, Month and Day child.

    :param element: DescriptorRecord
    :param name: Name of field with date
    :param is_required: flag, if field is required
    :return: datetime or None
    :raises: IndexError if date is missing
    """
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
    """
    Select text from node.

    :param element: DescriptorRecord
    :param name: Name of field with text
    :param is_required: flag, if field is required
    :return: text of field or empty string
    :raises: ValueError if field is missing
    """
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
    """
    Parse XML list. Execute func on children.

    :param element: Element with the list element
    :param name: Name of list element
    :param func: Callback to parse children
    :param children_required: flag, if children are required
    :return: List of items
    """
    return [func(x, children_required) for x in element.xpath(f"{name}/child::*")]


def get_attr(element, name):
    """
    Get attribute from element.

    :param element: Element
    :param name: Attribute name
    :return: Value of attribute
    """
    return element.get(name)


def get_element_text(element, is_required=False):
    """
    Get text from element

    :param element: Element
    :param is_required:
    :return: text of element
    """
    return element.text
