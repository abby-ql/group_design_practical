"use client";

import ReactECharts from "echarts-for-react";

interface RadarChartProps {
	data: { name: string; max: number; value: number }[];
	formatter?: (params: any) => string;
}

export function Radar({ data, formatter }: RadarChartProps): React.ReactNode {
	const option = {
		backgroundColor: "transparent",
		polar: {
			radius: "75%",
			center: ["50%", "50%"],
		},
		angleAxis: {
			type: "category",
			data: data.map((item) => item.name),
			axisLine: {
				show: true,
				lineStyle: {
					color: "#d1d5db",
				},
			},
			axisTick: {
				show: false,
			},
			axisLabel: {
				color: "#374151",
				fontSize: 11,
				margin: 15,
			},
		},
		radiusAxis: {
			min: 0,
			max: 100,
			axisLine: {
				show: true,
				lineStyle: {
					color: "#d1d5db",
				},
			},
			splitLine: {
				show: true,
				lineStyle: {
					color: "#e5e7eb",
					type: "dashed",
				},
			},
			splitArea: {
				show: true,
				areaStyle: {
					color: ["#f9fafb", "#ffffff"],
				},
			},
			axisLabel: {
				color: "#6b7280",
				fontSize: 10,
			},
		},
		series: [
			{
				type: "line",
				data: [
					...data.map((item) => (100 * item.value) / item.max),
					data.length > 0 ? (100 * data[0].value) / data[0].max : 0,
				],
				coordinateSystem: "polar",
				itemStyle: {
					color: "#3b82f6",
					borderColor: "#2563eb",
					borderWidth: 2,
				},
				areaStyle: {
					color: "rgba(59, 130, 246, 0.2)",
				},
				emphasis: {
					itemStyle: {
						color: "#2563eb",
						borderColor: "#1d4ed8",
						borderWidth: 3,
						shadowBlur: 10,
						shadowColor: "rgba(59, 130, 246, 0.5)",
					},
				},
			},
		],
		tooltip: {
			trigger: "axis",
			formatter:
				formatter ||
				((params: any) => {
					// When trigger is "axis", params is an array
					const paramArray = Array.isArray(params) ? params : [params];
					const firstParam = paramArray[0];

					if (
						firstParam &&
						firstParam.dataIndex !== undefined &&
						data[firstParam.dataIndex]
					) {
						const item = data[firstParam.dataIndex];
						const percentage =
							item.max > 0 ? Math.round((item.value / item.max) * 100) : 0;
						return `${item.name}: ${item.value}/${item.max} (${percentage}%)`;
					}
					return "No data available";
				}),
			backgroundColor: "#ffffff",
			borderColor: "#d1d5db",
			textStyle: {
				color: "#374151",
			},
		},
		grid: {
			containLabel: true,
			top: 0,
			bottom: 0,
			left: 0,
			right: 0,
		},
	};

	return (
		<div className="w-full">
			<ReactECharts
				option={option}
				style={{ height: "400px", width: "100%" }}
				opts={{ renderer: "svg" }}
			/>
		</div>
	);
}
