#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "endstone_blockdata/block_data_service.h"
namespace py=pybind11;
using namespace endstone_blockdata;
PYBIND11_MODULE(_endstone_blockdata,m){
    py::class_<BlockLocation>(m,"BlockLocation")
      .def(py::init<>()).def_readwrite("dimension",&BlockLocation::dimension)
      .def_readwrite("x",&BlockLocation::x).def_readwrite("y",&BlockLocation::y).def_readwrite("z",&BlockLocation::z);
    py::enum_<ConflictPolicy>(m,"ConflictPolicy")
      .value("FAIL_IF_CHANGED",ConflictPolicy::FailIfChanged).value("MERGE_CHANGED_PATHS",ConflictPolicy::MergeChangedPaths)
      .value("MERGE_INVENTORY_SLOTS",ConflictPolicy::MergeInventorySlots).value("REPLACE",ConflictPolicy::Replace).value("FORCE",ConflictPolicy::Force);
    py::class_<BlockSnapshot>(m,"BlockSnapshot").def_readonly("location",&BlockSnapshot::location)
      .def_readonly("type",&BlockSnapshot::type).def_readonly("runtime_id",&BlockSnapshot::runtime_id)
      .def_readonly("states",&BlockSnapshot::states).def_readonly("revision",&BlockSnapshot::revision);
}
