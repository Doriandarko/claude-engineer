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

def calculate_median(numbers: List[float]) -> float:
    """
    Calculate the median of a list of numbers.
    
    Args:
        numbers (List[float]): A list of numbers to find the median of
        
    Returns:
        float: The median value of the list
        
    Raises:
        ValueError: If the input list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate median of an empty list")
    
    sorted_numbers = sorted(numbers)
    n = len(sorted_numbers)
    mid = n // 2
    
    if n % 2 == 0:
        return (sorted_numbers[mid-1] + sorted_numbers[mid]) / 2
    else:
        return sorted_numbers[mid]

def main() -> None:
    """Main function to demonstrate the usage of calculate_sum and calculate_median."""
    try:
        numbers = [1, 2, 3, 4, 5]
        total = calculate_sum(numbers)
        median = calculate_median(numbers)
        print(f"The sum is: {total}")
        print(f"The median is: {median}")
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

class TestCalculateMedian(unittest.TestCase):
    """Test cases for the calculate_median function."""
    
    def test_odd_length_list(self):
        """Test median with odd number of elements."""
        self.assertEqual(calculate_median([1, 2, 3, 4, 5]), 3)
        
    def test_even_length_list(self):
        """Test median with even number of elements."""
        self.assertEqual(calculate_median([1, 2, 3, 4]), 2.5)
        
    def test_unordered_list(self):
        """Test median with unordered list."""
        self.assertEqual(calculate_median([5, 2, 1, 4, 3]), 3)
        
    def test_empty_list(self):
        """Test that empty list raises ValueError."""
        with self.assertRaises(ValueError):
            calculate_median([])
            
    def test_negative_numbers(self):
        """Test with negative numbers."""
        self.assertEqual(calculate_median([-1, -2, -3]), -2)

if __name__ == "__main__":
    main()
    # Run the tests
    unittest.main(argv=[''], exit=False)
