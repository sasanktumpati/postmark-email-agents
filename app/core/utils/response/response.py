from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    status: int = Field(..., description="Status code: 0 for success, 1 for failure")
    message: str = Field(..., min_length=1, description="Response message")
    data: Optional[T] = Field(None, description="Response data")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: int) -> int:
        if v not in [0, 1]:
            raise ValueError("Status must be 0 (success) or 1 (failure)")
        return v

    @classmethod
    def success(cls, message: str, data: Optional[T] = None) -> "BaseResponse[T]":
        """Create a success response"""
        return cls(status=0, message=message, data=data)

    @classmethod
    def error(cls, message: str, data: Optional[T] = None) -> "BaseResponse[T]":
        """Create an error response"""
        return cls(status=1, message=message, data=data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json()

    def __str__(self) -> str:
        return f"BaseResponse(status={self.status}, message='{self.message}')"

    def __repr__(self) -> str:
        return f"BaseResponse(status={self.status}, message='{self.message}', data={self.data})"


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
    ) -> "PaginatedResponse[T]":
        """Create a successful paginated response."""
        pagination = PaginationInfo.create(
            page=page, limit=limit, total_items=total_items
        )
        return cls(status=0, message=message, data=data, pagination=pagination)

    @classmethod
    def error(
        cls,
        message: str,
        page: int = 1,
        limit: int = 10,
        total_items: int = 0,
    ) -> "PaginatedResponse[T]":
        """Create an error paginated response."""
        pagination = PaginationInfo.create(
            page=page, limit=limit, total_items=total_items
        )
        return cls(status=1, message=message, data=[], pagination=pagination)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json()

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
