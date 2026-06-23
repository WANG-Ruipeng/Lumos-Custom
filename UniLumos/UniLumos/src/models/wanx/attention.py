import torch
import torch.nn.functional as F

try:
    from flash_attn import flash_attn_varlen_func
    FLASH_VER = 2
except ModuleNotFoundError:
    flash_attn_varlen_func = None
    FLASH_VER = None


print(f'[PreInfo] Use flash attention={FLASH_VER}')

__all__ = [
    'flash_attention',
]


def _unflatten_varlen(x, lengths, max_len):
    if bool(torch.all(lengths == max_len).item()):
        return x.unflatten(0, (int(lengths.numel()), max_len))

    padded = x.new_zeros((int(lengths.numel()), max_len, *x.shape[1:]))
    offset = 0
    for index, length in enumerate(lengths.tolist()):
        if length:
            padded[index, :length] = x[offset:offset + length]
        offset += length
    return padded


def _sdpa_attention(q, k, v, q_lens, k_lens, lq, lk, softmax_scale, causal, dropout_p):
    q = _unflatten_varlen(q, q_lens, lq)
    k = _unflatten_varlen(k, k_lens, lk)
    v = _unflatten_varlen(v, k_lens, lk)

    nq, nk = q.size(2), k.size(2)
    if nq != nk:
        if nq % nk != 0:
            raise ValueError(f"Query heads ({nq}) must be divisible by key/value heads ({nk}).")
        repeat = nq // nk
        k = k.repeat_interleave(repeat, dim=2)
        v = v.repeat_interleave(repeat, dim=2)

    q = q.transpose(1, 2)
    k = k.transpose(1, 2)
    v = v.transpose(1, 2)

    attn_mask = None
    if not bool(torch.all(k_lens == lk).item()):
        key_positions = torch.arange(lk, device=k.device)
        attn_mask = key_positions[None, :] < k_lens[:, None]
        attn_mask = attn_mask[:, None, None, :]

    if causal and attn_mask is not None:
        causal_mask = torch.ones((lq, lk), dtype=torch.bool, device=q.device).tril()
        attn_mask = attn_mask & causal_mask[None, None, :, :]
        causal = False

    x = F.scaled_dot_product_attention(
        q,
        k,
        v,
        attn_mask=attn_mask,
        dropout_p=dropout_p,
        is_causal=causal,
        scale=softmax_scale,
    )
    return x.transpose(1, 2).contiguous()


def flash_attention(
    q,
    k,
    v,
    q_lens=None,
    k_lens=None,
    dropout_p=0.,
    softmax_scale=None,
    q_scale=None,
    causal=False,
    window_size=(-1, -1),
    deterministic=False,
    dtype=torch.bfloat16
):
    """
    q:              [B, Lq, Nq, C1].
    k:              [B, Lk, Nk, C1].
    v:              [B, Lk, Nk, C2]. Nq must be divisible by Nk.
    q_lens:         [B].
    k_lens:         [B].
    dropout_p:      float. Dropout probability.
    softmax_scale:  float. The scaling of QK^T before applying softmax.
    causal:         bool. Whether to apply causal attention mask.
    window_size:    (left right). If not (-1, -1), apply sliding window local attention.
    deterministic:  bool. If True, slightly slower and uses more memory.
    dtype:          torch.dtype. Apply when dtype of q/k/v is not float16/bfloat16.
    """
    half_dtypes = (torch.float16, torch.bfloat16)
    assert dtype in half_dtypes
    assert q.device.type == 'cuda' and q.size(-1) <= 256

    # params
    b, lq, lk, out_dtype = q.size(0), q.size(1), k.size(1), q.dtype
    def half(x): return x if x.dtype in half_dtypes else x.to(dtype)

    # preprocess query
    if q_lens is None:
        q = half(q.flatten(0, 1))
        q_lens = torch.tensor(
            [lq] * b, dtype=torch.int32
        ).to(device=q.device, non_blocking=True)
    else:
        q = half(torch.cat([u[:v] for u, v in zip(q, q_lens)]))

    # preprocess key, value
    if k_lens is None:
        k = half(k.flatten(0, 1))
        v = half(v.flatten(0, 1))
        k_lens = torch.tensor(
            [lk] * b, dtype=torch.int32
        ).to(device=k.device, non_blocking=True)
    else:
        k = half(torch.cat([u[:v] for u, v in zip(k, k_lens)]))
        v = half(torch.cat([u[:v] for u, v in zip(v, k_lens)]))

    q = q.to(v.dtype)
    k = k.to(v.dtype)

    if q_scale is not None:
        q = q * q_scale
    # apply attention
    if FLASH_VER is None:
        if window_size != (-1, -1):
            raise NotImplementedError("PyTorch SDPA fallback only supports window_size=(-1, -1).")
        x = _sdpa_attention(q, k, v, q_lens, k_lens, lq, lk, softmax_scale, causal, dropout_p)
    elif FLASH_VER == 3:
        # Note: dropout_p, window_size are not supported in FA3 now.
        x = flash_attn_varlen_func(
            q=q,
            k=k,
            v=v,
            cu_seqlens_q=torch.cat([
                q_lens.new_zeros([1]), q_lens
            ]).cumsum(0, dtype=torch.int32).to(q.device, non_blocking=True),
            cu_seqlens_k=torch.cat([
                k_lens.new_zeros([1]), k_lens
            ]).cumsum(0, dtype=torch.int32).to(q.device, non_blocking=True),
            max_seqlen_q=lq,
            max_seqlen_k=lk,
            softmax_scale=softmax_scale,
            causal=causal,
            deterministic=deterministic
        )[0].unflatten(0, (b, lq))
    else:
        assert(FLASH_VER==2)
        x = flash_attn_varlen_func(
            q=q,
            k=k,
            v=v,
            cu_seqlens_q=torch.cat([
                q_lens.new_zeros([1]), q_lens
            ]).cumsum(0, dtype=torch.int32).to(q.device, non_blocking=True),
            cu_seqlens_k=torch.cat([
                k_lens.new_zeros([1]), k_lens
            ]).cumsum(0, dtype=torch.int32).to(q.device, non_blocking=True),
            max_seqlen_q=lq,
            max_seqlen_k=lk,
            dropout_p=dropout_p,
            softmax_scale=softmax_scale,
            causal=causal,
            window_size=window_size,
            deterministic=deterministic
        ).unflatten(0, (b, lq))
    
    # output
    return x.type(out_dtype)

