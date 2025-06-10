from typing import Any, Dict, Generic, List, Optional, TypeVar

from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    status: int = Field(..., description="Status code: 0 for success, 1 for failure")
    message: str = Field(..., min_length=1, description="Response message")
    data: Optional[T] = Field(None, description="Response data")
    http_status_code: int = Field(
        200, description="HTTP status code for the response", exclude=True
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: int) -> int:
        if v not in [0, 1]:
            raise ValueError("Status must be 0 (success) or 1 (failure)")
        return v

    @field_validator("http_status_code")
    @classmethod
    def validate_http_status_code(cls, v: int) -> int:
        if not (100 <= v <= 599):
            raise ValueError("HTTP status code must be between 100 and 599")
        return v

    @classmethod
    def success(
        cls,
        message: str,
        data: Optional[T] = None,
        http_status_code: int = http_status.HTTP_200_OK,
        headers: Optional[Dict[str, str]] = None,
    ) -> JSONResponse:
        """Create a success JSON response with appropriate HTTP status code"""
        response_data = cls(
            status=0,
            message=message,
            data=data,
            http_status_code=http_status_code,
        )
        return JSONResponse(
            content=response_data.model_dump(exclude_none=True),
            status_code=http_status_code,
            headers=headers or {},
        )

    @classmethod
    def failure(
        cls,
        message: str,
        data: Optional[T] = None,
        http_status_code: int = http_status.HTTP_400_BAD_REQUEST,
        headers: Optional[Dict[str, str]] = None,
    ) -> JSONResponse:
        """Create a failure JSON response with appropriate HTTP status code"""
        response_data = cls(
            status=1,
            message=message,
            data=data,
            http_status_code=http_status_code,
        )
        return JSONResponse(
            content=response_data.model_dump(exclude_none=True),
            status_code=http_status_code,
            headers=headers or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(exclude_none=True)

    def to_json_response(
        self, headers: Optional[Dict[str, str]] = None
    ) -> JSONResponse:
        """Convert to JSONResponse with appropriate HTTP status code"""
        return JSONResponse(
            content=self.model_dump(exclude_none=True),
            status_code=self.http_status_code,
            headers=headers or {},
        )

    def __str__(self) -> str:
        return f"BaseResponse(status={self.status}, message='{self.message}', http_status={self.http_status_code})"

    def __repr__(self) -> str:
        return f"BaseResponse(status={self.status}, message='{self.message}', data={self.data}, http_status={self.http_status_code})"


class PaginationInfo(BaseModel):
    """Model for Pagination Info."""

    page: int = Field(..., ge=1, description="Current page number (1-based)")
    limit: int = Field(..., ge=1, le=1000, description="Number of items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")

    @classmethod
    def create(cls, page: int, limit: int, total_items: int) -> "PaginationInfo":
        total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0
        has_next = page < total_pages
        has_previous = page > 1

        return cls(
            page=page,
            limit=limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )

    def __str__(self) -> str:
        return f"PaginationInfo(page={self.page}/{self.total_pages}, limit={self.limit}, total={self.total_items})"


class PaginatedResponse(BaseModel, Generic[T]):
    """Model for Paginated Responses."""

    status: int = Field(..., description="Status code: 0 for success, 1 for failure")
    message: str = Field(..., min_length=1, description="Response message")
    data: List[T] = Field(default_factory=list, description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    http_status_code: int = Field(
        200, description="HTTP status code for the response", exclude=True
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: int) -> int:
        if v not in [0, 1]:
            raise ValueError("Status must be 0 (success) or 1 (failure)")
        return v

    @classmethod
    def success(
        cls,
        message: str,
        data: List[T],
        page: int,
        limit: int,
        total_items: int,
        http_status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> "JSONResponse":
        """Create a successful paginated response."""
        pagination = PaginationInfo.create(
            page=page, limit=limit, total_items=total_items
        )
        response_data = cls(
            status=0,
            message=message,
            data=data,
            pagination=pagination,
            http_status_code=http_status_code,
        )
        return JSONResponse(
            content=response_data.model_dump(exclude_none=True),
            status_code=http_status_code,
            headers=headers or {},
        )

    @classmethod
    def failure(
        cls,
        message: str,
        page: int = 1,
        limit: int = 10,
        total_items: int = 0,
        http_status_code: int = 400,
        headers: Optional[Dict[str, str]] = None,
    ) -> "JSONResponse":
        """Create an error paginated response."""
        pagination = PaginationInfo.create(
            page=page, limit=limit, total_items=total_items
        )
        response_data = cls(
            status=1,
            message=message,
            data=[],
            pagination=pagination,
            http_status_code=http_status_code,
        )
        return JSONResponse(
            content=response_data.model_dump(exclude_none=True),
            status_code=http_status_code,
            headers=headers or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(exclude_none=True)

    def __str__(self) -> str:
        return f"PaginatedResponse(status={self.status}, message='{self.message}', items={len(self.data)})"

    def __repr__(self) -> str:
        return f"PaginatedResponse(status={self.status}, message='{self.message}', data={len(self.data)} items, pagination={self.pagination})"


class ErrorDetails(BaseModel):
    """Model for error information in responses."""

    error_code: str = Field(..., description="Specific error code")
    error_type: str = Field(
        ..., description="Type of error (validation, processing, etc.)"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    suggestions: Optional[str] = Field(None, description="Suggestions to fix the error")

    def __str__(self) -> str:
        return f"ErrorDetails(error_code='{self.error_code}', error_type='{self.error_type}')"
