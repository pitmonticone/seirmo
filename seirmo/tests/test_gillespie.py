#
# This file is part of seirmo (https://github.com/SABS-R3-Epidemiology/seirmo/)
# which is released under the BSD 3-clause license. See accompanying LICENSE.md
# for copyright notice and full license details.
#

import unittest
import numpy as np
from parameterized import parameterized
import random
from unittest.mock import MagicMock

import seirmo as se

numReps = 100


class TestGillespieFunc(unittest.TestCase):
    """Test the gillespie solve_gillespie function"""
    @classmethod
    def setUpClass(cls) -> None:
        cls.initial = np.array([10, 0])
        cls.t_span = [0, 10]
        cls.m = MagicMock()
        cls.m.return_value = np.array([[0, 1], [0, 0]])

    def test_t_span_input(self):
        """Ensure correct error handling for invalid t_span inputs"""
        with self.assertRaises(ValueError):  # t_span is 2D
            list(se.solve_gillespie(self.m, self.initial, t_span=[0]))
            # convert generator to list to force function to be evaluated#

        with self.assertRaises(ValueError):  # t_span must have range
            list(se.solve_gillespie(self.m, self.initial, t_span=[0, 0]))
        with self.assertRaises(ValueError):  # t_stop > t_start
            list(se.solve_gillespie(self.m, self.initial, t_span=[-2, 0]))
        with self.assertRaises(TypeError):  # time values must be floats
            list(se.solve_gillespie(self.m, self.initial, t_span=[0, 'ten']))

    @parameterized.expand([(random.random() * 100, random.random() * 100)
                           for _ in range(numReps)])
    def test_tspan_ordering(self, start, stop):
        test_span = [start, stop]
        if stop <= start:
            with self.assertRaises(ValueError):
                list(se.solve_gillespie(self.m, self.initial, test_span))

    def test_intial_input(self):
        with self.assertRaises(ValueError):  # initial conditions must be +ve
            list(se.solve_gillespie(self.m, np.array([-10, 0]), self.t_span))

    def test_propensity_call(self):
        m_count = MagicMock()
        m_count.return_value = np.array([[0, 1], [0, 0]])
        solve = se.solve_gillespie(m_count, self.initial, self.t_span)
        next(solve)  # return a yield
        self.assertEqual(m_count.call_count, 1,
                         'Propensity Func called unexpected number of times')
        next(solve)  # return a yield
        self.assertEqual(m_count.call_count, 2,
                         'Propensity Func called unexpected number of times')

    def test_neg_propensity(self):
        """Test error handling of negative elements in propensity matrix"""
        m_neg = MagicMock()
        m_neg.return_value = np.array([[0, -1], [0, 0]])
        solve = se.solve_gillespie(m_neg, self.initial, self.t_span)
        with self.assertRaises(ValueError):
            next(solve)

    def test_gillespie_output(self):
        def prop_func(x: np.ndarray):
            return np.array([[0, x[1]], [0, 0]])

        state = self.initial
        solve = se.solve_gillespie(prop_func, state, [0, 100])
        while True:
            try:
                output = next(solve)
            except StopIteration:
                break
            state = output[1:]
            self.assertTrue(np.all(state >= 0),
                            'Returned negative values in state array')

        self.assertEqual(state.tolist(), [0, 10],
                         'Unexpected output - incomplete infection')

    @parameterized.expand([(np.random.randint(0, 100, (2,)),)
                           for _ in range(numReps)])
    def test_gillespie_zeros(self, initial):
        """Ensure that zero propensity gives unchanged state for any initial"""
        m_zeros = MagicMock()
        m_zeros.return_value = np.array([[0, 0], [0, 0]])
        solution = list(se.solve_gillespie(m_zeros, initial, [0, 10]))
        final_sol = solution[-1][1:]  # take only compartment nums at end
        self.assertEqual(final_sol.tolist(), initial.tolist(),
                         'Unexpected output - changed state')

    @parameterized.expand([(np.random.randint(0, 100, (3,)),
                            np.random.rand(3, 3) * 100)
                           for _ in range(numReps)])
    def test_population_conservation(self, initial, propensity_mat):
        """Ensure population is conserved for any initial and prop matrix"""
        m_3dim = MagicMock()
        m_3dim.return_value = propensity_mat
        initial_pop = np.sum(initial)

        solve = se.solve_gillespie(m_3dim, initial, [0, 1])
        while True:
            try:
                output = next(solve)
            except StopIteration:
                break
            self.assertEqual(output.shape, (len(initial) + 1,),
                             'Unexpected number of output compartments')
            self.assertAlmostEqual(np.sum(output[1:]), initial_pop,
                                   'Unexpected output - pop. not conserved')


if __name__ == '__main__':
    unittest.main()
