from typing import List
import unittest

def calculate_sum(numbers: List[float]) -> float:
    """
    Calculate the sum of a list of numbers.
    
    Args:
        numbers (List[float]): A list of numbers to sum
        
    Returns:
        float: The sum of all numbers in the list
        
    Raises:
        ValueError: If the input list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate sum of an empty list")
    return sum(numbers)

def main() -> None:
    """Main function to demonstrate the usage of calculate_sum."""
    try:
        numbers = [1, 2, 3, 4, 5]
        total = calculate_sum(numbers)
        print(f"The sum is: {total}")
    except ValueError as e:
        print(f"Error: {e}")

class TestCalculateSum(unittest.TestCase):
    """Test cases for the calculate_sum function."""
    
    def test_normal_list(self):
        """Test with a normal list of numbers."""
        self.assertEqual(calculate_sum([1, 2, 3, 4, 5]), 15)
        
    def test_float_numbers(self):
        """Test with floating point numbers."""
        self.assertAlmostEqual(calculate_sum([1.5, 2.5, 3.5]), 7.5)
        
    def test_empty_list(self):
        """Test that empty list raises ValueError."""
        with self.assertRaises(ValueError):
            calculate_sum([])
            
    def test_negative_numbers(self):
        """Test with negative numbers."""
        self.assertEqual(calculate_sum([-1, -2, -3]), -6)

if __name__ == "__main__":
    main()
    # Run the tests
    unittest.main(argv=[''], exit=False)