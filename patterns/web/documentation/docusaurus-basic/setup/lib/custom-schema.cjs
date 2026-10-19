const { Joi } = require('@docusaurus/utils-validation');
const custom = Joi.object({
    home: Joi.object({
        heading: Joi.string().required(), body: Joi.string().required(), linkLabel: Joi.string().required(), linkTo: Joi.string().pattern(/^\//).required()
    }).required(),
    search: Joi.object({
        enabled: Joi.boolean().default(true), limit: Joi.number().integer().min(1).max(100).default(8), excerptLength: Joi.number().integer().min(20).max(1000).default(150), titleWeight: Joi.number().min(1).max(100).default(10), include: Joi.array().items(Joi.string()).default(['**']), exclude: Joi.array().items(Joi.string()).default([]), label: Joi.string().default('文書を検索'), placeholder: Joi.string().default('キーワードを入力…'), emptyMessage: Joi.string().default('文書名やキーワードで検索できます。'), noResultsMessage: Joi.string().default('一致する文書はありません。'), shortcut: Joi.string().length(1).default('k')
    }).required(),
}).required();
module.exports = custom;
