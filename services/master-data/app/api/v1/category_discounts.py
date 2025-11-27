# Copyright 2025 masa@kugel  # # Licensed under the Apache License, Version 2.0 (the "License");  # you may not use this file except in compliance with the License.  # You may obtain a copy of the License at  # #     http://www.apache.org/licenses/LICENSE-2.0  # # Unless required by applicable law or agreed to in writing, software  # distributed under the License is distributed on an "AS IS" BASIS,  # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  # See the License for the specific language governing permissions and  # limitations under the License.
from fastapi import APIRouter, status, HTTPException, Depends, Path, Query
from logging import getLogger
from typing import List
import inspect

from kugel_common.database import database as db_helper
from kugel_common.status_codes import StatusCodes
from kugel_common.security import get_tenant_id_with_security_by_query_optional, verify_tenant_id
from kugel_common.schemas.api_response import ApiResponse
from kugel_common.exceptions import (
    InvalidRequestDataException,
    DocumentAlreadyExistsException,
    DocumentNotFoundException,
    RepositoryException,
)

from app.config.settings import settings
from app.api.v1.schemas import (
    CategoryDiscountCreateRequest,
    CategoryDiscountUpdateRequest,
    CategoryDiscountResponse,
    CategoryDiscountDeleteResponse,
)
from app.api.v1.schemas_transformer import SchemasTransformerV1
from app.dependencies.get_master_services import get_category_discount_service_async
from app.dependencies.common import parse_sort

# Create a router instance for category master endpoints
router = APIRouter()

# Get a logger instance for this module
logger = getLogger(__name__)


@router.post(
    "/tenants/{tenant_id}/category_discounts",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[CategoryDiscountResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: StatusCodes.get(status.HTTP_400_BAD_REQUEST),
        status.HTTP_401_UNAUTHORIZED: StatusCodes.get(status.HTTP_401_UNAUTHORIZED),
        status.HTTP_422_UNPROCESSABLE_ENTITY: StatusCodes.get(status.HTTP_422_UNPROCESSABLE_ENTITY),
        status.HTTP_500_INTERNAL_SERVER_ERROR: StatusCodes.get(status.HTTP_500_INTERNAL_SERVER_ERROR),
    },
)
async def create_category_discount(
    category_discount: CategoryDiscountCreateRequest,
    tenant_id: str = Path(...),
    tenant_id_with_security: str = Depends(get_tenant_id_with_security_by_query_optional),
):
    """
    Create a new product category discount record.

    This endpoint allows creating a new category discount with its code, discountPercent,
    start date, and end date.

    Authentication is required via token or API key. The tenant ID in the path must match
    the one in the security credentials.

    Args:
        category_discount: The category details to create
        tenant_id: The tenant identifier from the path
        tenant_id_with_security: The tenant ID from security credentials

    Returns:
        ApiResponse[CategoryDiscountResponse]: Standard API response with the created category discount data

    Raises:
        DocumentAlreadyExistsException: If a category discount with the same code already exists
        InvalidRequestDataException: If the request data is invalid
        RepositoryException: If there's an error during database operations
    """
    logger.info(f"create_category_discount: category_discount->{category_discount}, tenant_id->{tenant_id}")
    verify_tenant_id(tenant_id, tenant_id_with_security, logger)
    service = await get_category_discount_service_async(tenant_id)
    try:
        new_category = await service.create_category_discount_async(
            category_discount_code=category_discount.category_discount_code,
            discount_percent=category_discount.discount_percent,
            start_date=category_discount.start_date,
            end_date=category_discount.end_date,
        )
        transformer = SchemasTransformerV1()
        return_category = transformer.transform_category_discount(new_category)
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise e

    response = ApiResponse(
        success=True,
        code=status.HTTP_201_CREATED,
        message=f"Category Discount {category_discount.category_discount_code} created successfully",
        data=return_category.model_dump(),
        operation=f"{inspect.currentframe().f_code.co_name}",
    )
    return response


@router.get(
    "/tenants/{tenant_id}/category_discounts",
    response_model=ApiResponse[List[CategoryDiscountResponse]],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: StatusCodes.get(status.HTTP_400_BAD_REQUEST),
        status.HTTP_401_UNAUTHORIZED: StatusCodes.get(status.HTTP_401_UNAUTHORIZED),
        status.HTTP_422_UNPROCESSABLE_ENTITY: StatusCodes.get(status.HTTP_422_UNPROCESSABLE_ENTITY),
        status.HTTP_500_INTERNAL_SERVER_ERROR: StatusCodes.get(status.HTTP_500_INTERNAL_SERVER_ERROR),
    },
)
async def get_category_discounts(
    tenant_id: str = Path(...),
    limit: int = Query(100),
    page: int = Query(1),
    sort: list[tuple[str, int]] = Depends(parse_sort),
    tenant_id_with_security: str = Depends(get_tenant_id_with_security_by_query_optional),
):
    """
    Retrieve all category discounts for a tenant.

    This endpoint returns a paginated list of all category discounts for the specified tenant.
    The results can be sorted and paginated as needed. This is typically used to populate
    category discount selection screens or to view all available category discounts for administration.

    Authentication is required via token or API key. The tenant ID in the path must match
    the one in the security credentials.

    Args:
        tenant_id: The tenant identifier from the path
        limit: Maximum number of categories to return (default: 100)
        page: Page number for pagination (default: 1)
        sort: Sorting criteria (default: category_discount_code ascending)
        tenant_id_with_security: The tenant ID from security credentials

    Returns:
        ApiResponse[List[CategoryDiscountResponse]]: Standard API response with a list of category discount data

    Raises:
        RepositoryException: If there's an error during database operations
    """
    logger.info(f"get_category_discount: tenant_id->{tenant_id}")
    verify_tenant_id(tenant_id, tenant_id_with_security, logger)
    service = await get_category_discount_service_async(tenant_id)
    try:
        paginated_result = await service.get_category_discounts_paginated_async(limit, page, sort)
        transformer = SchemasTransformerV1()
        return_categories = [transformer.transform_category_discount(category) for category in paginated_result.data]
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise e

    response = ApiResponse(
        success=True,
        code=status.HTTP_200_OK,
        message=f"Category discounts found successfully for tenant_id: {tenant_id}",
        data=[category.model_dump() for category in return_categories],
        metadata=paginated_result.metadata.model_dump(),
        operation=f"{inspect.currentframe().f_code.co_name}",
    )
    return response


@router.get(
    "/tenants/{tenant_id}/category_discounts/{category_discount_code}",
    response_model=ApiResponse[CategoryDiscountResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: StatusCodes.get(status.HTTP_400_BAD_REQUEST),
        status.HTTP_401_UNAUTHORIZED: StatusCodes.get(status.HTTP_401_UNAUTHORIZED),
        status.HTTP_404_NOT_FOUND: StatusCodes.get(status.HTTP_404_NOT_FOUND),
        status.HTTP_422_UNPROCESSABLE_ENTITY: StatusCodes.get(status.HTTP_422_UNPROCESSABLE_ENTITY),
        status.HTTP_500_INTERNAL_SERVER_ERROR: StatusCodes.get(status.HTTP_500_INTERNAL_SERVER_ERROR),
    },
)
async def get_category_discount(
    category_discount_code: str,
    tenant_id: str = Path(...),
    tenant_id_with_security: str = Depends(get_tenant_id_with_security_by_query_optional),
):
    """
    Retrieve a specific category discount by its code.

    This endpoint retrieves the details of a category discount identified by its unique code.
    It returns all attributes of the category discount.

    Authentication is required via token or API key. The tenant ID in the path must match
    the one in the security credentials.

    Args:
        category_discount_code: The unique code of the category discount to retrieve
        tenant_id: The tenant identifier from the path
        tenant_id_with_security: The tenant ID from security credentials

    Returns:
        ApiResponse[CategoryDiscountResponse]: Standard API response with the category data

    Raises:
        DocumentNotFoundException: If the category discount with the given code is not found
        RepositoryException: If there's an error during database operations
    """
    logger.info(f"get_category_discount: category_discount_code->{category_discount_code}, tenant_id->{tenant_id}")
    verify_tenant_id(tenant_id, tenant_id_with_security, logger)
    service = await get_category_discount_service_async(tenant_id)
    try:
        new_category = await service.get_category_discount_by_code_async(category_discount_code)
        if new_category is None:
            message = f"Category discount {category_discount_code} not found, tenant_id: {tenant_id}"
            raise DocumentNotFoundException(message, logger)
        transformer = SchemasTransformerV1()
        return_category = transformer.transform_category_discount(new_category)
    except Exception as e:
        logger.error(f"Error getting category: {e}")
        raise e

    response = ApiResponse(
        success=True,
        code=status.HTTP_200_OK,
        message=f"Category discount {category_discount_code} found successfully for tenant_id: {tenant_id}",
        data=return_category.model_dump(),
        operation=f"{inspect.currentframe().f_code.co_name}",
    )
    return response


@router.put(
    "/tenants/{tenant_id}/category_discounts/{category_discount_code}",
    response_model=ApiResponse[CategoryDiscountResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: StatusCodes.get(status.HTTP_400_BAD_REQUEST),
        status.HTTP_401_UNAUTHORIZED: StatusCodes.get(status.HTTP_401_UNAUTHORIZED),
        status.HTTP_404_NOT_FOUND: StatusCodes.get(status.HTTP_404_NOT_FOUND),
        status.HTTP_422_UNPROCESSABLE_ENTITY: StatusCodes.get(status.HTTP_422_UNPROCESSABLE_ENTITY),
        status.HTTP_500_INTERNAL_SERVER_ERROR: StatusCodes.get(status.HTTP_500_INTERNAL_SERVER_ERROR),
    },
)
async def update_category_discount(
    category_discount_code: str,
    category_discount: CategoryDiscountUpdateRequest,
    tenant_id: str = Path(...),
    tenant_id_with_security: str = Depends(get_tenant_id_with_security_by_query_optional),
):
    """
    Update an existing category discount.

    This endpoint allows updating the details of an existing category discount identified
    by its code. It can be used to modify the discount percent, start date, or end date.

    The category_discount_code itself cannot be changed, as it serves as a unique identifier.
    Updating a category will affect all products assigned to this category discount.

    Authentication is required via token or API key. The tenant ID in the path must match
    the one in the security credentials.

    Args:
        category_discount_code: The unique code of the category discount to update
        category_discount: The updated category discount details
        tenant_id: The tenant identifier from the path
        tenant_id_with_security: The tenant ID from security credentials

    Returns:
        ApiResponse[CategoryDiscountResponse]: Standard API response with the updated category discount data

    Raises:
        DocumentNotFoundException: If the category discount with the given code is not found
        InvalidRequestDataException: If the request data is invalid
        RepositoryException: If there's an error during database operations
    """
    logger.info(f"update_category_discount: category_discount->{category_discount}, tenant_id->{tenant_id}")
    verify_tenant_id(tenant_id, tenant_id_with_security, logger)
    service = await get_category_discount_service_async(tenant_id)
    try:
        updated_category = await service.update_category_discount_async(
            category_discount_code=category_discount_code, update_data=category_discount.model_dump()
        )
        if updated_category is None:
            message = f"Category discount {category_discount_code} not found, tenant_id: {tenant_id}"
            raise DocumentNotFoundException(message, logger)
        transformer = SchemasTransformerV1()
        return_category = transformer.transform_category_discount(updated_category)
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        raise e

    response = ApiResponse(
        success=True,
        code=status.HTTP_200_OK,
        message=f"Category discount {category_discount_code} updated successfully for tenant_id: {tenant_id}",
        data=return_category.model_dump(),
        operation=f"{inspect.currentframe().f_code.co_name}",
    )
    return response


@router.delete(
    "/tenants/{tenant_id}/category_discounts/{category_discount_code}",
    response_model=ApiResponse[CategoryDiscountDeleteResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: StatusCodes.get(status.HTTP_400_BAD_REQUEST),
        status.HTTP_401_UNAUTHORIZED: StatusCodes.get(status.HTTP_401_UNAUTHORIZED),
        status.HTTP_404_NOT_FOUND: StatusCodes.get(status.HTTP_404_NOT_FOUND),
        status.HTTP_422_UNPROCESSABLE_ENTITY: StatusCodes.get(status.HTTP_422_UNPROCESSABLE_ENTITY),
        status.HTTP_500_INTERNAL_SERVER_ERROR: StatusCodes.get(status.HTTP_500_INTERNAL_SERVER_ERROR),
    },
)
async def delete_category_discount(
    category_discount_code: str,
    tenant_id: str = Path(...),
    tenant_id_with_security: str = Depends(get_tenant_id_with_security_by_query_optional),
):
    """
    Delete a category discount.

    This endpoint allows removing a category discount completely from the system.
    Caution should be exercised as deleting category discounts that have products assigned
    to them may cause inconsistencies in the data. It's recommended to reassign
    products to other categories before deleting a category discount.

    Authentication is required via token or API key. The tenant ID in the path must match
    the one in the security credentials.

    Args:
        category_discount_code: The unique code of the category discount to delete
        tenant_id: The tenant identifier from the path
        tenant_id_with_security: The tenant ID from security credentials

    Returns:
        ApiResponse[CategoryDiscountDeleteResponse]: Standard API response with deletion confirmation

    Raises:
        DocumentNotFoundException: If the category discount with the given code is not found
        RepositoryException: If there's an error during database operations
    """
    logger.info(f"delete_category_discount: category_discount_code->{category_discount_code}, tenant_id->{tenant_id}")
    verify_tenant_id(tenant_id, tenant_id_with_security, logger)
    service = await get_category_discount_service_async(tenant_id)
    try:
        await service.delete_category_discount_async(category_discount_code)
    except Exception as e:
        logger.error(f"Error deleting category discount: {e} for tenant_id: {tenant_id}")
        raise e

    response = ApiResponse(
        success=True,
        code=status.HTTP_200_OK,
        message=f"Category discount {category_discount_code} deleted successfully for tenant_id: {tenant_id}",
        data=CategoryDiscountDeleteResponse(category_discount_code=category_discount_code).model_dump(),
        operation=f"{inspect.currentframe().f_code.co_name}",
    )
    return response
