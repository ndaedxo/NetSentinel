#!/usr/bin/env python3
"""
Distributed Training Support for NetSentinel ML Components

Provides multi-GPU and distributed training capabilities for anomaly detection models
"""

import os
import torch
import torch.nn as nn
import torch.distributed as dist
import torch.multiprocessing as mp
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler
from typing import Dict, List, Optional, Any, Callable, Union
import logging
from contextlib import contextmanager
import warnings

# Import new core components
try:
    from ..core.base import BaseComponent
    from ..utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger

logger = create_logger("distributed_training", level="INFO")


class DistributedTrainingConfig:
    """Configuration for distributed training"""

    def __init__(
        self,
        world_size: int = 1,
        backend: str = "nccl",  # "nccl" for GPU, "gloo" for CPU
        master_addr: str = "localhost",
        master_port: str = "12355",
        use_gpu: bool = True,
        find_unused_parameters: bool = False,
        gradient_accumulation_steps: int = 1,
        mixed_precision: bool = False,
    ):
        self.world_size = world_size
        self.backend = backend
        self.master_addr = master_addr
        self.master_port = master_port
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.find_unused_parameters = find_unused_parameters
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.mixed_precision = mixed_precision


class DistributedTrainer(BaseComponent):
    """
    Distributed training coordinator for ML models

    Supports:
    - Multi-GPU training with DDP
    - Single GPU training
    - CPU training fallback
    - Gradient accumulation
    - Mixed precision training
    """

    def __init__(
        self,
        name: str = "distributed_trainer",
        config: Optional[DistributedTrainingConfig] = None,
        model_factory: Optional[Callable] = None,
    ):
        """
        Initialize distributed trainer

        Args:
            name: Component name
            config: Distributed training configuration
            model_factory: Function to create model instances
        """
        super().__init__(name, {}, logger)

        self.config = config or DistributedTrainingConfig()
        self.model_factory = model_factory

        # Training state
        self.is_distributed = False
        self.rank = 0
        self.local_rank = 0
        self.world_size = 1

        # GPU setup
        self.device = torch.device("cuda" if self.config.use_gpu else "cpu")
        self.gpu_count = torch.cuda.device_count() if self.config.use_gpu else 0

        # Mixed precision
        self.scaler = torch.cuda.amp.GradScaler() if self.config.mixed_precision and self.config.use_gpu else None

        logger.info(f"Distributed trainer initialized with {self.gpu_count} GPUs available")

    def setup_distributed(self, rank: int = 0, world_size: Optional[int] = None):
        """
        Setup distributed training environment

        Args:
            rank: Process rank
            world_size: Total number of processes
        """
        if world_size is None:
            world_size = self.gpu_count if self.config.use_gpu else 1

        if world_size <= 1:
            logger.info("Single process training - no distributed setup needed")
            return

        self.rank = rank
        self.world_size = world_size
        self.is_distributed = True

        # Set environment variables
        os.environ['MASTER_ADDR'] = self.config.master_addr
        os.environ['MASTER_PORT'] = self.config.master_port
        os.environ['WORLD_SIZE'] = str(world_size)
        os.environ['RANK'] = str(rank)

        # Initialize process group
        dist.init_process_group(
            backend=self.config.backend,
            rank=rank,
            world_size=world_size
        )

        # Set device for this process
        if self.config.use_gpu:
            torch.cuda.set_device(rank)
            self.device = torch.device(f"cuda:{rank}")

        logger.info(f"Distributed training setup complete: rank {rank}/{world_size} on {self.device}")

    def cleanup_distributed(self):
        """Clean up distributed training"""
        if self.is_distributed:
            dist.destroy_process_group()
            self.is_distributed = False
            logger.info("Distributed training cleanup complete")

    def create_distributed_model(self, model: nn.Module) -> nn.Module:
        """
        Wrap model for distributed training

        Args:
            model: PyTorch model

        Returns:
            Distributed model (DDP wrapped if distributed)
        """
        model = model.to(self.device)

        if self.is_distributed:
            model = DDP(
                model,
                device_ids=[self.local_rank] if self.config.use_gpu else None,
                output_device=self.local_rank if self.config.use_gpu else None,
                find_unused_parameters=self.config.find_unused_parameters
            )
            logger.info("Model wrapped with DistributedDataParallel")
        else:
            logger.info("Single process model - no DDP wrapping")

        return model

    def create_distributed_dataloader(self, dataset: torch.utils.data.Dataset, batch_size: int, shuffle: bool = True) -> DataLoader:
        """
        Create distributed data loader

        Args:
            dataset: PyTorch dataset
            batch_size: Batch size per GPU
            shuffle: Whether to shuffle data

        Returns:
            Distributed data loader
        """
        if self.is_distributed:
            sampler = DistributedSampler(
                dataset,
                num_replicas=self.world_size,
                rank=self.rank,
                shuffle=shuffle
            )
            dataloader = DataLoader(
                dataset,
                batch_size=batch_size,
                sampler=sampler,
                num_workers=0,  # Avoid issues with multiprocessing
                pin_memory=self.config.use_gpu
            )
            logger.info(f"Created distributed dataloader with sampler")
        else:
            dataloader = DataLoader(
                dataset,
                batch_size=batch_size,
                shuffle=shuffle,
                num_workers=4,
                pin_memory=self.config.use_gpu
            )
            logger.info("Created single-process dataloader")

        return dataloader

    def distributed_backward(self, loss: torch.Tensor, optimizer: torch.optim.Optimizer):
        """
        Perform backward pass with distributed training considerations

        Args:
            loss: Loss tensor
            optimizer: Optimizer
        """
        # Scale loss for gradient accumulation
        loss = loss / self.config.gradient_accumulation_steps

        # Mixed precision backward
        if self.scaler is not None:
            self.scaler.scale(loss).backward()
        else:
            loss.backward()

    def step_optimizer(self, optimizer: torch.optim.Optimizer):
        """
        Step optimizer with distributed training considerations

        Args:
            optimizer: Optimizer
        """
        if self.scaler is not None:
            # Mixed precision optimizer step
            self.scaler.step(optimizer)
            self.scaler.update()
        else:
            optimizer.step()

    def reduce_tensor(self, tensor: torch.Tensor) -> torch.Tensor:
        """
        Reduce tensor across all processes (average)

        Args:
            tensor: Tensor to reduce

        Returns:
            Reduced tensor
        """
        if self.is_distributed:
            dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
            tensor = tensor / self.world_size

        return tensor

    def barrier(self):
        """Synchronization barrier for all processes"""
        if self.is_distributed:
            dist.barrier()

    def is_main_process(self) -> bool:
        """Check if this is the main process (rank 0)"""
        return self.rank == 0

    def log_distributed(self, message: str, level: str = "info"):
        """Log only from main process to avoid spam"""
        if self.is_main_process():
            if level == "info":
                logger.info(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "error":
                logger.error(message)
            elif level == "debug":
                logger.debug(message)

    def save_checkpoint(self, model: nn.Module, optimizer: torch.optim.Optimizer, epoch: int, loss: float, path: str):
        """
        Save training checkpoint

        Args:
            model: Model to save
            optimizer: Optimizer state
            epoch: Current epoch
            loss: Current loss
            path: Save path
        """
        if not self.is_main_process():
            return

        checkpoint = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': loss,
            'rank': self.rank,
            'world_size': self.world_size,
        }

        if self.scaler is not None:
            checkpoint['scaler_state_dict'] = self.scaler.state_dict()

        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved to {path}")

    def load_checkpoint(self, model: nn.Module, optimizer: torch.optim.Optimizer, path: str) -> Dict[str, Any]:
        """
        Load training checkpoint

        Args:
            model: Model to load into
            optimizer: Optimizer to load into
            path: Checkpoint path

        Returns:
            Checkpoint metadata
        """
        checkpoint = torch.load(path, map_location=self.device)

        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

        if self.scaler is not None and 'scaler_state_dict' in checkpoint:
            self.scaler.load_state_dict(checkpoint['scaler_state_dict'])

        logger.info(f"Checkpoint loaded from {path}")
        return checkpoint

    @contextmanager
    def autocast_context(self):
        """Context manager for mixed precision training"""
        if self.scaler is not None:
            with torch.cuda.amp.autocast():
                yield
        else:
            yield

    def get_training_stats(self) -> Dict[str, Any]:
        """Get distributed training statistics"""
        return {
            "is_distributed": self.is_distributed,
            "rank": self.rank,
            "world_size": self.world_size,
            "device": str(self.device),
            "gpu_count": self.gpu_count,
            "mixed_precision": self.scaler is not None,
            "gradient_accumulation_steps": self.config.gradient_accumulation_steps,
            "backend": self.config.backend,
        }


def spawn_distributed_training(
    world_size: int,
    train_function: Callable,
    model_factory: Optional[Callable] = None,
    config: Optional[DistributedTrainingConfig] = None,
    *args,
    **kwargs
):
    """
    Spawn distributed training processes

    Args:
        world_size: Number of processes to spawn
        train_function: Training function to run
        model_factory: Model factory function
        config: Distributed training config
        *args, **kwargs: Additional arguments for train_function
    """
    if world_size <= 1:
        # Single process training
        logger.info("Starting single-process training")
        trainer = DistributedTrainer(config=config, model_factory=model_factory)
        train_function(trainer, *args, **kwargs)
    else:
        # Multi-process distributed training
        logger.info(f"Starting distributed training with {world_size} processes")

        # Set start method for multiprocessing
        try:
            mp.set_start_method('spawn', force=True)
        except RuntimeError:
            pass  # Already set

        # Spawn processes
        mp.spawn(
            _distributed_worker,
            args=(world_size, train_function, model_factory, config, args, kwargs),
            nprocs=world_size,
            join=True
        )


def _distributed_worker(
    rank: int,
    world_size: int,
    train_function: Callable,
    model_factory: Optional[Callable],
    config: Optional[DistributedTrainingConfig],
    args: tuple,
    kwargs: dict
):
    """
    Worker function for distributed training

    Args:
        rank: Process rank
        world_size: Total world size
        train_function: Training function
        model_factory: Model factory
        config: Training config
        args: Positional args for train_function
        kwargs: Keyword args for train_function
    """
    try:
        # Create trainer and setup distributed training
        trainer = DistributedTrainer(config=config, model_factory=model_factory)
        trainer.setup_distributed(rank, world_size)

        # Run training function
        train_function(trainer, *args, **kwargs)

    except Exception as e:
        logger.error(f"Error in distributed worker {rank}: {e}")
        raise
    finally:
        trainer.cleanup_distributed()


# Convenience functions for common use cases
def get_optimal_world_size() -> int:
    """Get optimal world size based on available GPUs"""
    if torch.cuda.is_available():
        return torch.cuda.device_count()
    return 1


def is_distributed_available() -> bool:
    """Check if distributed training is available"""
    return torch.cuda.is_available() and torch.cuda.device_count() > 1


def auto_configure_distributed() -> DistributedTrainingConfig:
    """Auto-configure distributed training based on available resources"""
    gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0

    config = DistributedTrainingConfig(
        world_size=gpu_count if gpu_count > 0 else 1,
        use_gpu=gpu_count > 0,
        backend="nccl" if gpu_count > 0 else "gloo",
        mixed_precision=gpu_count > 0,  # Enable mixed precision for GPU training
    )

    return config


# BaseComponent abstract methods
async def _initialize(self):
    """Initialize distributed trainer"""
    logger.info("Distributed trainer initialized")

async def _start_internal(self):
    """Start distributed trainer operations"""
    pass

async def _stop_internal(self):
    """Stop distributed trainer operations"""
    self.cleanup_distributed()

async def _cleanup(self):
    """Cleanup distributed trainer resources"""
    self.cleanup_distributed()
