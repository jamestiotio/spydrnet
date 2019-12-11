import sys
import itertools
import weakref
from enum import Enum


class Element(object):
    """
    Base class of all intermediate representation objects.

    An intermediate representation object represents an item in a netlist. Items range in specificity from pins on a
    port or wires in a cable up to an item that represents the netlist as a whole.

    Each element implements a dictionary for storing key-value pairs. The key should be a case sensitive string and the
    value should be a primitive type (string, integer, float, boolean) or potentially nested collections of primitive
    types. The purpose of this dictionary is to provide a space for properties and metadata associated with the element.

    Key namespaces are separated with a *period* character. If the key is void of a *period* than the key resides in the
    root namespace. Keys in the root namespace are considered properties. Other keys are considered metadata. For
    example '<LANG_OF_ORIGIN>.<METADATA_TAG>':<metadata_value> is considered metadata associated with the netlist's
    language of origin.

    Only data pertinent to the netlist should be stored in this dictionary. Cached data (namespace management, anything
    that can be recreated from the netlist) should be excluded from this dictionary. The intent of the IR is to house
    the basis of data for the netlist.

    The only key that is reserved is 'NAME'. It is the primary name of the element. NAME may be undefined or inferred,
    for example, a pin on a port may be nameless, but infer its name for its parent port and position.
    """
    __slots__ = ['_data']

    def __init__(self):
        """
        Initialize an element with an empty data dictionary.
        """
        self._data = dict()

    def __setitem__(self, key, value):
        '''
        create an entry in the dictionary of the element it will be stored in the metadata.
        '''
        key = sys.intern(key)
        self._data.__setitem__(sys.intern(key), value)

    def __delitem__(self, key):
        self._data.__delitem__(key)

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __contains__(self, item):
        return self._data.__contains__(item)

    def __iter__(self):
        return self._data.__iter__()

    def pop(self, item):
        return self._data.pop(item)


class Netlist(Element):
    """
    Represents a netlist object.

    Contains a top level instance and libraries
    """
    __slots__ = ['_libraries', '_top_instance']

    def __init__(self):
        super().__init__()
        self._libraries = list()
        self._top_instance = None

    @property
    def libraries(self):
        """get a list of all libraries included in the netlist"""
        return ListView(self._libraries)

    @libraries.setter
    def libraries(self, value):
        """set the libraries. This function can only be used to reorder the libraries. Use the remove_library and add_library functions to add and remove libraries."""
        assert set(self._libraries) == set(value), "Set of values do not match, this assignment can only reorder values"
        self._libraries = list(value)

    @property
    def top_instance(self):
        """
        Get the top instance in the netlist.

        Returns
        -------
        Instance
            The top level instance in the environment
        """
        return self._top_instance

    @top_instance.setter
    def top_instance(self, instance):
        '''sets the top instance of the design. The instance must not be null and should probably come from this netlist'''
        assert instance is None or isinstance(instance, Instance), "Must specify an instance"
        # TODO: should We have a DRC that makes sure the instance is of a definition contained in netlist? I think no but I am open to hear other points of veiw.
        self._top_instance = instance

    def create_library(self):
        '''create a library and add it to the netlist and return that library'''
        library = Library()
        self.add_library(library)
        return library
    
    def add_library(self, library, position=None):
        '''add an already existing library to the netlist. This library should not belong to another netlist. Use remove_library from other netlists before adding'''
        assert library not in self._libraries, "Library already included in netlist"
        assert library.netlist is None, "Library already belongs to a different netlist"
        if position is not None:
            self._libraries.insert(position, library)
        else:
            self._libraries.append(library)
        library._netlist = self

    def remove_library(self, library):
        '''removes the given library if it is in the netlist'''
        self._remove_library(library)
        self._libraries.remove(library)

    def remove_libraries_from(self, libraries):
        '''removes all the given libraries from the netlist. All libraries must be in the netlist'''
        if isinstance(libraries, set):
            excluded_libraries = libraries
        else:
            excluded_libraries = set(libraries)
        assert all(x.netlist == self for x in excluded_libraries), "Some libraries to remove are not included in " \
                                                                   "netlist "
        included_libraries = list()
        for library in self._libraries:
            if library not in excluded_libraries:
                included_libraries.append(library)
            else:
                self._remove_library(library)
        self._libraries = included_libraries

    def _remove_library(self, library):
        '''internal function which will separate a particular libraries binding from the netlist'''
        assert library.netlist == self, "Library is not included in netlist"
        library._netlist = None


class Library(Element):
    """
    Represents a library object.

    Contains a pointer to parent netlist and definitions.
    """
    __slots__ = ['_netlist', '_definitions']

    def __init__(self):
        super().__init__()
        self._netlist = None
        self._definitions = list()

    @property
    def netlist(self):
        '''get the netlist that contins this libarary'''
        return self._netlist

    @property
    def definitions(self):
        '''return a list of all the definitions that are included in this library'''
        return ListView(self._definitions)

    @definitions.setter
    def definitions(self, value):
        '''set the definitions to a new reordered set of definitions. This function cannot be used to add or remove defintions'''
        assert set(self._definitions) == set(value), "Set of values do not match, this function can only reorder values"
        self._definitions = list(value)

    def create_definition(self):
        '''create a definition, add it to the library, and return the definition'''
        definition = Definition()
        self.add_definition(definition)
        return definition

    def add_definition(self, definition, position=None):
        '''add an existing definition to the library. The definition must not belong to a library including this one. '''
        assert definition.library is not self, "Definition already included in library"
        assert definition.library is None, "Definition already belongs to a different library"
        if position is not None:
            self._definitions.insert(position, definition)
        else:
            self._definitions.append(definition)
        definition._library = self

    def remove_definition(self, definition):
        '''remove the given defintion from the library'''
        self._remove_definition(definition)
        self._definitions.remove(definition)

    def remove_definitions_from(self, definitions):
        '''remove a set of definitions from the library. all definitions provdied must be in the library'''
        if isinstance(definitions, set):
            excluded_definitions = definitions
        else:
            excluded_definitions = set(definitions)
        assert all(x.library == self for x in excluded_definitions), "Some definitions to remove are not included in " \
                                                                     "the library "
        included_definitions = list()
        for definition in self._definitions:
            if definition not in excluded_definitions:
                included_definitions.append(definition)
            else:
                self._remove_definition(definition)
        self._definitions = included_definitions

    def _remove_definition(self, definition):
        assert definition.library == self, "Library is not included in netlist"
        definition._library = None


class Definition(Element):
    """
    Represents a definition of a cell, module, entity/architecture, or paralleled structure object.

    Contains a pointer to parent library, ports, cables, and instances.
    """
    __slots__ = ['_library', '_ports', '_cables', '_children', '_references']

    def __init__(self):
        super().__init__()
        self._library = None
        self._ports = list()
        self._cables = list()
        self._children = list()
        self._references = set()

    @property
    def library(self):
        '''Get the library that contains this definition'''
        return self._library

    @property
    def ports(self):
        '''get the ports that are instanced in this definition'''
        return ListView(self._ports)

    @ports.setter
    def ports(self, value):
        '''Reorder ports that are instanced in this definition. Use remove_port and add_port to remove and add ports respectively'''
        target = list(value)
        assert set(self._ports) == set(target), "Set of values do not match, this function can only reorder values"
        self._ports = target

    @property
    def cables(self):
        '''get the cables that are instanced in this definition'''
        return ListView(self._cables)

    @cables.setter
    def cables(self, value):
        '''Reorder the cables in this definition. Use add_cable and remove_cable to add or remove cables.'''
        target = list(value)
        assert set(self._cables) == set(target), "Set of values do not match, this function can only reorder values"
        self._cables = target

    @property
    def children(self):
        '''return a list of all instances instantiated in this definition'''
        return ListView(self._children)

    @children.setter
    def children(self, value):
        '''reorder the list of instances instantiated in this definition use add_child and remove_child to add or remove instances to or from the definition'''
        target = list(value)
        assert set(self._children) == set(target), "Set of values do not match, this function can only reorder values"
        self._children = target

    @property
    def references(self):
        '''get a list of all the instances of this definition'''
        return SetView(self._references)

    def is_leaf(self):
        '''check to see if this definition represents a leaf cell. Leaf cells are cells with no children instances or no children cables. Blackbox cells are considered leaf cells as well as direct pass through cells with cables only'''
        if len(self._children) > 0 or len(self._cables) > 0:
            return False
        return True

    def create_port(self):
        '''create a port, add it to the definition, and return that port'''
        port = Port()
        self.add_port(port)
        return port

    def add_port(self, port, position=None):
        '''add a preexisting port to the definition. this port must not be a member of any definition for this function to work'''
        assert port.definition is not self, "Port already included in definition"
        assert port.definition is None, "Port already belongs to a different definition"
        if position is not None:
            self._ports.insert(position, port)
        else:
            self._ports.append(port)
        port._definition = self

    def remove_port(self, port):
        '''remove a port from the definition. This port must be a member of the definition in order to be removed'''
        self._remove_port(port)
        self._ports.remove(port)

    def remove_ports_from(self, ports):
        '''remove a set of ports from the definition. All these ports must be included in the definition'''
        if isinstance(ports, set):
            excluded_ports = ports
        else:
            excluded_ports = set(ports)
        assert all(x.definition == self for x in excluded_ports), "Some ports to remove are not included in the " \
                                                                  "definition."
        included_ports = list()
        for port in self._ports:
            if port not in excluded_ports:
                included_ports.append(port)
            else:
                self._remove_port(port)
        self._ports = included_ports

    def _remove_port(self, port):
        '''internal function to dissociate the port from the definition'''
        assert port.definition == self, "Port is not included in definition"
        port._definition = None

    def create_child(self):
        '''create an instance to add to the definition, add it, and return the instance.'''
        instance = Instance()
        self.add_child(instance)
        return instance
    
    def add_child(self, instance, position=None):
        '''Add an existing instance to the definition. This instance must not already be included in a definition'''
        assert instance.parent is not self, "Instance already included in definition"
        assert instance.parent is None, "Instance already belongs to a different definition"
        if position is not None:
            self._children.insert(position, instance)
        else:
            self._children.append(instance)
        instance._parent = self

    def remove_child(self, instance):
        '''remove an instance from the definition. The instance must be a member of the definition already'''
        self._remove_child(instance)
        self._children.remove(instance)

    def remove_children_from(self, children):
        '''remove a set of instances from the definition. All instances must be members of the definition'''
        if isinstance(children, set):
            excluded_children = children
        else:
            excluded_children = set(children)
        assert all(x.parent == self for x in excluded_children), "Some children are not parented by the definition"
        included_children = list()
        for child in self._children:
            if child not in excluded_children:
                included_children.append(child)
            else:
                self._remove_child(child)
        self._children = included_children

    def _remove_child(self, child):
        '''internal function for dissociating a child instance from the definition.'''
        assert child.parent == self, "Instance is not included in definition"
        child._parent = None

    def create_cable(self):
        '''create a cable, add it to the definition, and return the cable.'''
        cable = Cable()
        self.add_cable(cable)
        return cable

    def add_cable(self, cable, position=None):
        '''add a cable to the definition. The cable must not already be a member of another definition.'''
        assert cable.definition is not self, "Cable already included in definition"
        assert cable.definition is None, "Cable already belongs to a different definition"
        if position is not None:
            self._cables.insert(position, cable)
        else:
            self._cables.append(cable)
        cable._definition = self

    def remove_cable(self, cable):
        '''remove a cable from the definition. The cable must be a member of the definition.'''
        self._remove_cable(cable)
        self._cables.remove(cable)

    def remove_cables_from(self, cables):
        '''remove a set of cables from the definition. The cables must be members of the definition'''
        if isinstance(cables, set):
            excluded_cables = cables
        else:
            excluded_cables = set(cables)
        assert all(x.definition == self for x in excluded_cables), "Some cables are not included in the definition"
        included_cables = list()
        for cable in self._cables:
            if cable not in excluded_cables:
                included_cables.append(cable)
            else:
                self._remove_cable(cable)
        self._cables = included_cables

    def _remove_cable(self, cable):
        '''dissociate the cable from this definition. This function is internal and should not be called.'''
        assert cable.definition == self, "Cable is not included in definition"
        cable._definition = None


class Bundle(Element):
    __slots__ = ['_definition', '_is_downto', '_is_scalar', '_lower_index']

    def __init__(self):
        super().__init__()
        self._definition = None
        self._is_downto = True
        self._is_scalar = True
        self._lower_index = 0

    @property
    def definition(self):
        return self._definition

    @property
    def is_downto(self):
        return self._is_downto

    @is_downto.setter
    def is_downto(self, value):
        self._is_downto = value

    def _items(self):
        return None

    @property
    def is_scalar(self):
        _items = self._items()
        if _items and len(_items) > 1:
            return False
        return self._is_scalar

    @is_scalar.setter
    def is_scalar(self, value):
        _items = self._items()
        if _items and len(_items) > 0 and value is True:
            raise RuntimeError("Cannot set is_scalar to True on a multi-item bundle")
        else:
            self._is_scalar = value

    @property
    def is_array(self):
        return not self.is_scalar

    @is_array.setter
    def is_array(self, value):
        _items = self._items()
        if _items and len(_items) > 0 and value is False:
            raise RuntimeError("Cannot set is_array to False on a multi-item bundle")
        else:
            self._is_scalar = not value

    @property
    def lower_index(self):
        return self._lower_index

    @lower_index.setter
    def lower_index(self, value):
        self._lower_index = value


class Port(Bundle):
    __slots__ = ['_direction', '_pins']

    class Direction(Enum):
        """
        Define the possible directions for a given port
        """
        UNDEFINED = 0
        INOUT = 1
        IN = 2
        OUT = 3
    
    def __init__(self):
        """
        setup an empty port
        """
        super().__init__()
        self._direction = self.Direction.UNDEFINED
        self._pins = list()

    def _items(self):
        return self._pins

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        if isinstance(value, self.Direction):
            self._direction = value
        elif isinstance(value, int):
            for direction in self.Direction:
                if direction.value == value:
                    self._direction = direction
                    break
        elif isinstance(value, str):
            value = value.lower()
            for direction in self.Direction:
                if direction.name.lower() == value:
                    self._direction = direction
                    break
        else:
            raise TypeError(f"Type {type(value)} cannot be assigned to direction")

    @property
    def pins(self):
        return ListView(self._pins)

    def initialize_pins(self, pin_count):
        """
        create pin_count pins in the given port a downto style syntax is assumed
        Parameters:
        pin_count : this is the number of pins to add to the port
        """
        for _ in range(pin_count):
            self.create_pin()

    def create_pin(self):
        """
        create a pin and add it to the port.
        return:
        the inner_pin created
        """
        pin = InnerPin()
        self.add_pin(pin)
        return pin

    def add_pin(self, pin, position=None):
        """
        add a pin to the port in an unsafe fashion. The calling class must take care of the indicies.
        """
        assert isinstance(pin, InnerPin)
        assert pin.port is not self, "Pin already belongs to this port"
        assert pin.port is None, "Pin already belongs to another port"
        if position is None:
            self._pins.append(pin)
        else:
            self._pins.insert(position, pin)
        pin._port = self

    def remove_pin(self, pin):
        self._remove_pin(pin)
        self._pins.remove(pin)

    def remove_pins_from(self, pins):
        if isinstance(pins, set):
            exclude_pins = pins
        else:
            exclude_pins = set(pins)
        assert all(isinstance(x, InnerPin) and x.port == self for x in exclude_pins), "All pins to remove must be " \
                                                                                      "InnerPins and belong to the port"
        include_pins = list()
        for pin in self._pins:
            if pin not in exclude_pins:
                include_pins.append(pin)
            else:
                self._remove_pin(pin)
        self._pins = include_pins

    def _remove_pin(self, pin):
        assert pin.port == self, "Pin does not belong to this port."
        pin._port = None


class Pin:
    __slots__ = ['_wire']

    def __init__(self):
        self._wire = None

    @property
    def wire(self):
        return self._wire


class InnerPin(Pin):
    def __init__(self):
        super().__init__()
        self._port = None

    @property
    def port(self):
        return self._port


class OuterPin(Pin):
    def __init__(self):
        super().__init__()
        self.instance = None
        self.inner_pin = None


class Cable(Bundle):
    def __init__(self):
        super().__init__()
        self.wires = list()

    def _items(self):
        return self.wires

    def initialize_wires(self, wire_count):
        for _ in range(wire_count):
            self.create_wire()

    def create_wire(self):
        wire = Wire()
        self.add_wire(wire)
        return wire

    def add_wire(self, wire):
        self.wires.append(wire)
        wire.cable = self


class Wire:
    def __init__(self):
        self.cable = None
        self.pins = list()

    def connect_pin(self, pin):
        self.pins.append(pin)
        pin.wire = self
        
    def disconnect_pin(self, pin):
        self.pins.remove(pin)
        pin.wire = None


class Instance(Element):
    """
    netlist instance of a netlist definition
    """
    __slots__ = ['_parent', '_reference', '_pins']

    def __init__(self):
        """
        creates an empty object of type instance
        """
        super().__init__()
        self._parent = None
        self._reference = None
        self._pins = dict()

    @property
    def parent(self):
        return self._parent

    @property
    def reference(self):
        return self._reference

    @reference.setter
    def reference(self, value):
        self._reference = value

    def is_leaf(self):
        """
        check to see if the netlist instance is an instance of a leaf definition
        Returns
        -------
        boolean
            True if the definition is leaf
            False if the definition is not leaf
        """
        return self._reference.is_leaf()


class ListView:
    __slots__ = ['_list', '__add__', '__getitem__', '__contains__', '__eq__', '__hash__', '__ge__', '__gt__',
                 '__iter__', '__le__', '__len__', '__lt__', '__ne__', '__mul__', '__rmul__', '__reversed__', '__repr__',
                 '__str__', 'copy', 'count', 'index', '__iadd__', '__imul__']

    def __init__(self, list_object):
        assert isinstance(list_object, list)
        self._list = list_object
        for attr in self.__slots__[1:-2]:
            exec(f"self.{attr} = list_object.{attr}")
        for attr in self.__slots__[-2:]:
            exec(f"self.{attr} = self.unsupported_operator")

    def __radd__(self, other):
        return other + self._list

    def unsupported_operator(self, other):
        raise TypeError("unsupported operator for type SetView")


class SetView:
    __slots__ = ['__and__', '__rand__', '__eq__', '__ge__', '__gt__', '__hash__', '__iter__', '__le__', '__len__',
                 '__lt__', '__ne__', '__or__', '__ror__', '__sub__', '__rsub__', '__xor__', '__rxor__', '__repr__',
                 '__str__', 'copy', 'difference', 'intersection', 'isdisjoint', 'issubset', 'issuperset',
                 'symmetric_difference', 'union', '__iand__', '__ior__', '__ixor__', '__isub__']

    def __init__(self, set_object):
        assert isinstance(set_object, set)
        for attr in self.__slots__[:-4]:
            exec(f"self.{attr} = set_object.{attr}")
        for attr in self.__slots__[-4:]:
            exec(f"self.{attr} = self.unsupported_operator")

    def unsupported_operator(self, other):
        raise TypeError("unsupported operator for type SetView")
