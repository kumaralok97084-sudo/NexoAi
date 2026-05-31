from __future__ import annotations

import asyncio
import socket
import ssl
import subprocess
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class HostingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="pinghost", description="Ping a host to check latency.")
    async def pinghost(self, interaction: discord.Interaction, host: str) -> None:
        await interaction.response.defer()
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-n", "4", host,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
            output = stdout.decode(errors="ignore")[:1500]
            await interaction.followup.send(f"```\n{output}\n```")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            await interaction.followup.send(f"Ping to `{host}` timed out or failed.")

    @app_commands.command(name="dns", description="DNS lookup for a domain.")
    async def dns_lookup(self, interaction: discord.Interaction, domain: str) -> None:
        await interaction.response.defer()
        try:
            result = socket.getaddrinfo(domain, 80)
            ips = sorted(set(r[4][0] for r in result))
            lines = [f"**{domain}** resolves to:"]
            for ip in ips[:10]:
                lines.append(f"`{ip}`")
            await interaction.followup.send("\n".join(lines))
        except socket.gaierror:
            await interaction.followup.send(f"Could not resolve `{domain}`.")

    @app_commands.command(name="whois", description="Quick WHOIS lookup (uses system whois).")
    async def whois_lookup(self, interaction: discord.Interaction, domain: str) -> None:
        await interaction.response.defer()
        try:
            proc = await asyncio.create_subprocess_exec(
                "whois", domain,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stdout.decode(errors="ignore")[:1500]
            await interaction.followup.send(f"```\n{output}\n```")
        except FileNotFoundError:
            await interaction.followup.send("WHOIS is not installed on this system.")

    @app_commands.command(name="sslcheck", description="Check SSL certificate for a domain.")
    async def ssl_check(self, interaction: discord.Interaction, domain: str, port: int = 443) -> None:
        await interaction.response.defer()
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=domain) as sock:
                sock.settimeout(10)
                sock.connect((domain, port))
                cert = sock.getpeercert()
            issuer = dict(cert.get("issuer", [])).get("organizationName", "Unknown")
            subject = dict(cert.get("subject", [])).get("commonName", domain)
            expires = cert.get("notAfter", "Unknown")

            embed = discord.Embed(title=f"SSL Certificate: {domain}", color=discord.Color.green())
            embed.add_field(name="Subject", value=subject, inline=True)
            embed.add_field(name="Issuer", value=issuer, inline=True)
            embed.add_field(name="Expires", value=str(expires)[:19], inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            await interaction.followup.send(f"SSL check failed: `{exc}`")

    @app_commands.command(name="portscan", description="Scan common ports on a host.")
    async def port_scan(self, interaction: discord.Interaction, host: str) -> None:
        await interaction.response.defer()
        common_ports = [21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, 1433, 3306, 3389, 5432, 6379, 8080, 8443, 27017]
        open_ports = []
        for port in common_ports:
            try:
                _, _ = await asyncio.wait_for(
                    asyncio.get_event_loop().sock_connect(socket.socket(socket.AF_INET, socket.SOCK_STREAM), (host, port)),
                    timeout=2,
                )
                open_ports.append(port)
            except Exception:
                pass
        if open_ports:
            await interaction.followup.send(f"Open ports on `{host}`: `{' '.join(str(p) for p in open_ports)}`")
        else:
            await interaction.followup.send(f"No common ports open on `{host}`.")

    @app_commands.command(name="traceroute", description="Trace route to a host.")
    async def trace_route(self, interaction: discord.Interaction, host: str) -> None:
        await interaction.response.defer()
        try:
            proc = await asyncio.create_subprocess_exec(
                "tracert", "-h", "15", host,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode(errors="ignore")[:1500]
            await interaction.followup.send(f"```\n{output}\n```")
        except FileNotFoundError:
            await interaction.followup.send("Traceroute not available on this system.")

    @app_commands.command(name="httpcheck", description="Check if a website is reachable.")
    async def http_check(self, interaction: discord.Interaction, url: str) -> None:
        await interaction.response.defer()
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, follow_redirects=True)
                embed = discord.Embed(title=f"HTTP Check: {url}", color=discord.Color.green() if resp.is_success else discord.Color.red())
                embed.add_field(name="Status", value=f"{resp.status_code} {resp.reason_phrase}", inline=True)
                embed.add_field(name="Response Time", value=f"{resp.elapsed.total_seconds():.2f}s", inline=True)
                embed.add_field(name="Content Length", value=f"{len(resp.content):,} bytes", inline=True)
                await interaction.followup.send(embed=embed)
        except Exception as exc:
            await interaction.followup.send(f"Failed to reach `{url}`: `{exc}`")

    @app_commands.command(name="headers", description="View HTTP headers of a URL.")
    async def http_headers(self, interaction: discord.Interaction, url: str) -> None:
        await interaction.response.defer()
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, follow_redirects=True)
            lines = [f"`{k}: {v}`" for k, v in dict(resp.headers).items()][:20]
            await interaction.followup.send(f"**Headers for {url}**\n" + "\n".join(lines))
        except Exception as exc:
            await interaction.followup.send(f"Failed: `{exc}`")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HostingCog(bot))
