#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
native_while_loop(PyObject *self, PyObject *args) {
    PyObject *visitor;
    PyObject *cond_node;
    PyObject *body_list;
    PyObject *visit_method;
    PyObject *break_exc;
    PyObject *continue_exc;

    if (!PyArg_ParseTuple(args, "OOOOOO", &visitor, &cond_node, &body_list, &break_exc, &continue_exc, &visit_method))
        return NULL;

    while (1) {
        PyObject *cond_res = PyObject_CallFunctionObjArgs(visit_method, cond_node, NULL);
        if (!cond_res) return NULL;

        int cond_truth = PyObject_IsTrue(cond_res);
        Py_DECREF(cond_res);
        if (cond_truth <= 0) break;

        Py_ssize_t i, n = PyList_Size(body_list);
        for (i = 0; i < n; i++) {
            PyObject *stmt = PyList_GetItem(body_list, i);
            PyObject *res = PyObject_CallFunctionObjArgs(visit_method, stmt, NULL);
            if (!res) {
                if (PyErr_ExceptionMatches(break_exc)) {
                    PyErr_Clear();
                    goto loop_break;
                }
                if (PyErr_ExceptionMatches(continue_exc)) {
                    PyErr_Clear();
                    goto loop_continue;
                }
                return NULL;
            }
            Py_DECREF(res);
        }
    loop_continue:
        ;
    }

loop_break:
    Py_RETURN_NONE;
}

static PyObject *
native_for_loop(PyObject *self, PyObject *args) {
    PyObject *visitor;
    PyObject *iterable_expr;
    PyObject *var_name;
    PyObject *body_list;
    PyObject *env;
    PyObject *break_exc;
    PyObject *continue_exc;
    PyObject *visit_method;

    if (!PyArg_ParseTuple(args, "OOOOOOOO", &visitor, &iterable_expr, &var_name, &body_list, &env, &break_exc, &continue_exc, &visit_method))
        return NULL;

    PyObject *iterable = PyObject_CallFunctionObjArgs(visit_method, iterable_expr, NULL);
    if (!iterable) return NULL;

    if (!PyObject_HasAttrString(iterable, "__iter__")) {
        Py_DECREF(iterable);
        PyErr_SetString(PyExc_TypeError, "Object is not iterable");
        return NULL;
    }

    PyObject *iterator = PyObject_GetIter(iterable);
    Py_DECREF(iterable);
    if (!iterator) return NULL;

    while (1) {
        PyObject *item = PyIter_Next(iterator);
        if (!item) break;

        PyObject *vars_dict = PyObject_GetAttrString(env, "vars");
        if (vars_dict && PyDict_Check(vars_dict)) {
            if (PyDict_SetItem(vars_dict, var_name, item) < 0) {
                Py_DECREF(item);
                Py_DECREF(vars_dict);
                Py_DECREF(iterator);
                return NULL;
            }
            Py_DECREF(vars_dict);
        } else if (vars_dict) {
            Py_DECREF(vars_dict);
            PyObject *res = PyObject_CallMethod(env, "define", "sO", PyUnicode_AsUTF8(var_name), item);
            if (!res) {
                Py_DECREF(item);
                Py_DECREF(iterator);
                return NULL;
            }
            Py_DECREF(res);
        }

        Py_DECREF(item);

        Py_ssize_t i, n = PyList_Size(body_list);
        for (i = 0; i < n; i++) {
            PyObject *stmt = PyList_GetItem(body_list, i);
            PyObject *res = PyObject_CallFunctionObjArgs(visit_method, stmt, NULL);
            if (!res) {
                if (PyErr_ExceptionMatches(break_exc)) {
                    PyErr_Clear();
                    goto loop_break;
                }
                if (PyErr_ExceptionMatches(continue_exc)) {
                    PyErr_Clear();
                    goto loop_continue;
                }
                Py_DECREF(iterator);
                return NULL;
            }
            Py_DECREF(res);
        }
    loop_continue:
        ;
    }
loop_break:
    Py_DECREF(iterator);
    Py_RETURN_NONE;
}

static PyObject *
native_c_style_for_loop(PyObject *self, PyObject *args) {
    PyObject *visitor;
    PyObject *init_stmt;
    PyObject *condition;
    PyObject *increment;
    PyObject *body_list;
    PyObject *break_exc;
    PyObject *continue_exc;
    PyObject *visit_method;

    if (!PyArg_ParseTuple(args, "OOOOOOOO", &visitor, &init_stmt, &condition, &increment, &body_list, &break_exc, &continue_exc, &visit_method))
        return NULL;

    if (init_stmt != Py_None) {
        PyObject *res = PyObject_CallFunctionObjArgs(visit_method, init_stmt, NULL);
        if (!res) return NULL;
        Py_DECREF(res);
    }

    while (1) {
        if (condition != Py_None) {
            PyObject *cond_result = PyObject_CallFunctionObjArgs(visit_method, condition, NULL);
            if (!cond_result) return NULL;

            PyObject *cond_value = cond_result;
            if (PyTuple_Check(cond_result) && PyTuple_Size(cond_result) == 3) {
                cond_value = PyTuple_GetItem(cond_result, 0);
            }

            int is_true = PyObject_IsTrue(cond_value);
            Py_DECREF(cond_result);

            if (is_true <= 0) {
                if (is_true < 0) return NULL;
                break;
            }
        }

        Py_ssize_t i, n = PyList_Size(body_list);
        for (i = 0; i < n; i++) {
            PyObject *stmt = PyList_GetItem(body_list, i);
            PyObject *res = PyObject_CallFunctionObjArgs(visit_method, stmt, NULL);
            if (!res) {
                if (PyErr_ExceptionMatches(break_exc)) {
                    PyErr_Clear();
                    goto loop_break;
                }
                if (PyErr_ExceptionMatches(continue_exc)) {
                    PyErr_Clear();
                    goto loop_continue;
                }
                return NULL;
            }
            Py_DECREF(res);
        }

    loop_continue:
        if (increment != Py_None) {
            PyObject *res = PyObject_CallFunctionObjArgs(visit_method, increment, NULL);
            if (!res) return NULL;
            Py_DECREF(res);
        }
    }

loop_break:
    Py_RETURN_NONE;
}

static PyMethodDef NativeLoopMethods[] = {
    {"native_while_loop", native_while_loop, METH_VARARGS, "Native while loop"},
    {"native_for_loop", native_for_loop, METH_VARARGS, "Native for loop"},
    {"native_c_style_for_loop", native_c_style_for_loop, METH_VARARGS, "Native C-style for loop"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef nativeloopmodule = {
    PyModuleDef_HEAD_INIT,
    "native_loop",
    NULL,
    -1,
    NativeLoopMethods
};

PyMODINIT_FUNC
PyInit_native_loop(void) {
    return PyModule_Create(&nativeloopmodule);
}
