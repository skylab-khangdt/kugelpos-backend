# Copyright 2025 masa@kugel  # # Licensed under the Apache License, Version 2.0 (the "License");  # you may not use this file except in compliance with the License.  # You may obtain a copy of the License at  # #     http://www.apache.org/licenses/LICENSE-2.0  # # Unless required by applicable law or agreed to in writing, software  # distributed under the License is distributed on an "AS IS" BASIS,  # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  # See the License for the specific language governing permissions and  # limitations under the License.
from logging import getLogger
from datetime import datetime

from kugel_common.exceptions import DocumentNotFoundException, DocumentAlreadyExistsException, ServiceException
from app.models.documents.category_discounts_document import CategoryDiscountDocument
from app.models.repositories.category_discounts_repository import CategoryDiscountRepository

logger = getLogger(__name__)


def _validate_date_format(date_str: str, param_name: str) -> None:
    """
    Validate that a date string is in YYYYMMDD format and represents a valid date.
    
    Args:
        date_str: The date string to validate
        param_name: The name of the parameter (for error messages)
    
    Raises:
        ServiceException: If the date format is invalid or the date is not valid
    """
    if not date_str:
        return
    
    # Check if the string is exactly 8 characters and all digits
    if len(date_str) != 8 or not date_str.isdigit():
        message = f"Invalid date format: {date_str}"
        raise ServiceException(message, logger)
    
    # Try to parse the date
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        message = f"Invalid date: {date_str}"
        raise ServiceException(message, logger)


def _validate_date_range(start_date: str, end_date: str) -> None:
    """
    Validate that start_date is before end_date.
    
    Args:
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
    
    Raises:
        ServiceException: If start_date is not before end_date
    """
    if start_date and end_date:
        if start_date >= end_date:
            message = f"Invalid date range: start_date must be before end_date"
            raise ServiceException(message, logger)


class CategoryDiscountService:
    """
    Service class for managing category discount data operations.
    This service provides business logic for creating, retrieving, updating,
    and deleting category discount records in the master data database.
    """

    def __init__(self, category_discount_repo: CategoryDiscountRepository):
        """
        Initialize the CategoryDiscountService with a repository.

        Args:
            category_discount_repo: Repository for category discount data operations
        """
        self.category_discount_repo = category_discount_repo

    async def create_category_discount_async(
        self, category_discount_code: str, discount_percent: float, start_date: str, end_date: str
    ) -> CategoryDiscountDocument:
        """
        Create a new category discount in the database.

        Args:
            category_discount_code: Unique identifier for the category
            discount_percent: Discount percent of the category
            start_date: Start date of the category
            end_date: End date of the category

        Returns:
            Newly created CategoryDiscountDocument

        Raises:
            DocumentAlreadyExistsException: If a category discount with the given code already exists
            ServiceException: If date format or date range is invalid
        """
        # Validate date format and range
        _validate_date_format(start_date, "start_date")
        _validate_date_format(end_date, "end_date")
        _validate_date_range(start_date, end_date)

        # check if category discount exists
        category_discount = await self.category_discount_repo.get_category_discount_by_code_async(category_discount_code)
        if category_discount is not None:
            message = f"category discount with code {category_discount_code} already exists. tenant_id: {category_discount.tenant_id}"
            raise DocumentAlreadyExistsException(message, logger)

        category_doc = CategoryDiscountDocument()
        category_doc.category_discount_code = category_discount_code
        category_doc.discount_percent = discount_percent
        category_doc.start_date = start_date
        category_doc.end_date = end_date
        if discount_percent < 0 or discount_percent > 100:
            message = f"Invalid discount percentage: {discount_percent}"
            raise ServiceException(message, logger)
        return await self.category_discount_repo.create_category_discount_async(category_doc)

    async def get_category_discount_by_code_async(self, category_discount_code: str) -> CategoryDiscountDocument:
        """
        Retrieve a category discount by its unique code.

        Args:
            category_discount_code: Unique identifier for the category

        Returns:
            CategoryDiscountDocument with the specified code

        Raises:
            DocumentNotFoundException: If no category with the given code exists
        """
        category_discount = await self.category_discount_repo.get_category_discount_by_code_async(category_discount_code)
        if category_discount is None:
            message = f"category discount with code {category_discount_code} not found"
            raise DocumentNotFoundException(message, logger)
        return category_discount

    async def get_category_discounts_async(self) -> list:
        """
        Retrieve all category discounts within the tenant with pagination and sorting.

        Returns:
            List of CategoryDiscountDocument objects
        """
        return await self.category_discount_repo.get_all_category_discount_async({})

    async def get_category_discounts_paginated_async(self, limit: int, page: int, sort: list[tuple[str, int]]):
        """
        Retrieve all category discounts within the tenant with pagination metadata.

        Args:
            limit: Maximum number of records to return
            page: Page number for pagination
            sort: List of tuples containing field name and sort direction (1 for ascending, -1 for descending)

        Returns:
            PaginatedResult containing CategoryDiscountDocument objects and metadata
        """
        return await self.category_discount_repo.get_category_discount_by_filter_paginated_async({}, limit, page, sort)

    async def update_category_discount_async(self, category_discount_code: str, update_data: dict) -> CategoryDiscountDocument:
        """
        Update an existing category discount with new data.

        Args:
            category_discount_code: Unique identifier for the category discount to update
            update_data: Dictionary containing the fields to update and their new values

        Returns:
            Updated CategoryDiscountDocument

        Raises:
            DocumentNotFoundException: If no category with the given code exists
            ServiceException: If date format or date range is invalid
        """
        # Check if category exists first
        existing_discount = await self.category_discount_repo.get_category_discount_by_code_async(category_discount_code)
        if existing_discount is None:
            message = f"category discount with code {category_discount_code} not found"
            raise DocumentNotFoundException(message, logger)
        
        # Validate date format if dates are being updated
        if "start_date" in update_data:
            _validate_date_format(update_data["start_date"], "start_date")
        if "end_date" in update_data:
            _validate_date_format(update_data["end_date"], "end_date")
        
        # Validate date range - use existing dates if not in update_data
        start_date = update_data.get("start_date", existing_discount.start_date)
        end_date = update_data.get("end_date", existing_discount.end_date)
        
        if start_date and end_date:
            _validate_date_range(start_date, end_date)

        # update category discount
        return await self.category_discount_repo.update_category_discount_async(category_discount_code, update_data)

    async def delete_category_discount_async(self, category_discount_code: str) -> None:
        """
        Delete a category discount from the database.

        Args:
            category_discount_code: Unique identifier for the category to delete

        Raises:
            DocumentNotFoundException: If no category with the given code exists
        """
        # check if category discount exists
        category_discount = await self.category_discount_repo.get_category_discount_by_code_async(category_discount_code)
        if category_discount is None:
            message = f"category discount with code {category_discount_code} not found"
            raise DocumentNotFoundException(message, logger)

        # delete category discount
        return await self.category_discount_repo.delete_category_discount_async(category_discount_code)
