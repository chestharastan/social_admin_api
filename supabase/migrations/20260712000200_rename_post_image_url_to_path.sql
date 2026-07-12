do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_images'
          and column_name = 'image_url'
    ) and not exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'post_images'
          and column_name = 'image_path'
    ) then
        alter table public.post_images rename column image_url to image_path;
    end if;
end;
$$;
